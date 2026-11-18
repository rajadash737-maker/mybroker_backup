"""Read-only privilege audit for the isolated Site Visit MySQL test account.

This script performs no database writes. It suppresses connection and SQL error
details so credentials, URLs, and raw grant rows are never printed.
"""

from __future__ import annotations

import json
import numbers
import os
import re
import sys
from collections import defaultdict

from sqlalchemy import URL, create_engine, text


APPROVED_DATABASE = "mybroker_sitevisit_test_0174e41d408a4d31bdb3012ae84c2d51"
APPROVED_USERNAME = "mybroker_sitevisit_test_admin"
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1"}
ENV_KEYS = (
    "SITE_VISIT_TEST_MYSQL_HOST",
    "SITE_VISIT_TEST_MYSQL_PORT",
    "SITE_VISIT_TEST_MYSQL_USER",
    "SITE_VISIT_TEST_MYSQL_PASSWORD",
)
REQUIRED_TABLE_PRIVILEGES = {
    "users": {"SELECT", "INSERT"},
    "sell_land_requests": {"SELECT", "INSERT"},
    "site_visit_requests": {"SELECT", "INSERT", "UPDATE"},
    "razorpay_payment_orders": {"SELECT", "INSERT", "UPDATE"},
    "razorpay_webhook_logs": {"SELECT", "INSERT", "UPDATE"},
}
REQUIRED_TABLES = set(REQUIRED_TABLE_PRIVILEGES)


class AuditFailure(Exception):
    """A secret-free audit failure category."""


def _database_error_category(error: Exception) -> str:
    """Classify database errors without exposing driver messages or SQL."""
    original = getattr(error, "orig", error)
    args = getattr(original, "args", ())
    code = args[0] if args and type(args[0]) is int else None
    if code in {1044, 1045, 1142, 1143, 1227, 1370}:
        return "permission_denied"
    if code in {1054, 1064, 1109, 1146, 1193, 1235}:
        return "unsupported_query_or_metadata"
    return "unknown_database_error"


def _privilege_name(value) -> str:
    name = str(value).strip().upper()
    if re.fullmatch(r"[A-Z_ ]+", name):
        return name
    raise AuditFailure("unrecognized privilege metadata")


def _quote_identifier(value: str, identifier_preparer) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise AuditFailure("role metadata is not safely representable")
    return identifier_preparer.quote_identifier(value)


def _grant_row_category(grant: str) -> str:
    if re.search(
        r"\bON\s+(?:PROCEDURE|FUNCTION)\s+.+?\s+TO\b", grant, re.IGNORECASE
    ):
        return "routine grant"
    upper = grant.upper()
    if "WITH GRANT OPTION" in upper or "WITH ADMIN OPTION" in upper:
        return "grant option"
    if re.search(r"\bGRANT\s+PROXY\s+ON\b", grant, re.IGNORECASE):
        return "proxy grant"
    if re.match(r"\s*GRANT\s+USAGE\s+ON\s+\*\.\*\s+TO\b", grant, re.IGNORECASE):
        return "usage grant"
    if re.search(r"\bON\s+\*\s*\.\s*\*\s+TO\b", grant, re.IGNORECASE):
        return "global grant"
    if re.search(r"\bON\s+.+?\s*\.\s*\*\s+TO\b", grant, re.IGNORECASE):
        return "schema grant"
    if re.search(r"\bON\s+`[^`]+`\s*\.\s*`[^`]+`\s+TO\b", grant, re.IGNORECASE):
        return "table grant"
    if re.match(r"\s*GRANT\s+.+?\s+TO\b", grant, re.IGNORECASE) and not re.search(
        r"\bON\b", grant, re.IGNORECASE
    ):
        return "role assignment"
    return "unsupported grant format"


def _pattern_matches(database_pattern: str, database_name: str, partial_revokes: bool) -> bool:
    """Conservatively evaluate MySQL database grant wildcards for visible schemas."""
    regex_parts = ["^"]
    index = 0
    while index < len(database_pattern):
        char = database_pattern[index]
        if char == "\\" and index + 1 == len(database_pattern):
            raise AuditFailure("schema grant pattern cannot be safely interpreted")
        if char == "\\":
            index += 1
            regex_parts.append(re.escape(database_pattern[index]))
        elif not partial_revokes and char == "%":
            regex_parts.append(".*")
        elif not partial_revokes and char == "_":
            regex_parts.append(".")
        else:
            regex_parts.append(re.escape(char))
        index += 1
    regex_parts.append("$")
    return re.fullmatch("".join(regex_parts)[1:-1], database_name) is not None


def _has_active_wildcard(database_pattern: str, partial_revokes: bool) -> bool:
    index = 0
    while index < len(database_pattern):
        char = database_pattern[index]
        if char == "\\":
            if index + 1 == len(database_pattern):
                raise AuditFailure("schema grant pattern cannot be safely interpreted")
            index += 2
            continue
        if not partial_revokes and char in {"%", "_"}:
            return True
        index += 1
    return False


def _normalize_partial_revokes(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, numbers.Number) and not isinstance(value, complex):
        if value == 0:
            return False
        if value == 1:
            return True
        raise AuditFailure("partial revokes metadata is unsupported")
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized == "ON":
            return True
        if normalized == "OFF":
            return False
    raise AuditFailure("partial revokes metadata is unsupported")


def _emit(result: str, checks: dict, details: dict | None = None, exit_code: int = 0) -> None:
    report = {"result": result, "checks": checks}
    if details is not None:
        report["details"] = details
    print(json.dumps(report, sort_keys=True))
    raise SystemExit(exit_code)


def main() -> None:
    missing = [key for key in ENV_KEYS if not os.environ.get(key)]
    if missing:
        _emit("FAIL", {"connection_settings_present": False}, exit_code=1)

    host = os.environ["SITE_VISIT_TEST_MYSQL_HOST"].strip().lower()
    username = os.environ["SITE_VISIT_TEST_MYSQL_USER"]
    if host not in ALLOWED_HOSTS or username != APPROVED_USERNAME:
        _emit("FAIL", {"configured_host_and_user_approved": False}, exit_code=1)

    try:
        port = int(os.environ["SITE_VISIT_TEST_MYSQL_PORT"])
    except ValueError:
        _emit("FAIL", {"configured_port_valid": False}, exit_code=1)
    if not 1 <= port <= 65535:
        _emit("FAIL", {"configured_port_valid": False}, exit_code=1)

    engine = None
    stage = "connection_setup"
    checks = {
        "configured_host_and_user_approved": True,
        "configured_port_valid": True,
        "current_account_exact": False,
        "login_identity_matches_approved_account": False,
        "approved_database_selected": False,
        "privilege_metadata_readable": False,
        "roles_inspected": False,
        "proxy_mappings_inspected": False,
        "no_unapproved_privilege_paths": False,
        "table_privileges_match_allowlist": False,
    }
    try:
        engine = create_engine(
            URL.create(
                "mysql+pymysql",
                username=username,
                password=os.environ["SITE_VISIT_TEST_MYSQL_PASSWORD"],
                host=host,
                port=port,
                database=APPROVED_DATABASE,
            ),
            pool_pre_ping=True,
        )

        identifier_preparer = engine.dialect.identifier_preparer
        with engine.connect() as connection:
            stage = "identity_and_server_settings"
            current_user, login_user, database_name, partial_revokes, mandatory_roles, current_roles = (
                connection.execute(
                    text(
                        "SELECT CURRENT_USER(), USER(), DATABASE(), "
                        "@@GLOBAL.partial_revokes, @@GLOBAL.mandatory_roles, CURRENT_ROLE()"
                    )
                ).one()
            )
            current_parts = str(current_user).rsplit("@", 1)
            login_parts = str(login_user).rsplit("@", 1)
            if len(current_parts) != 2 or current_parts[0] != APPROVED_USERNAME:
                raise AuditFailure("authenticated account identity mismatch")
            authenticated_host = current_parts[1].lower()
            if authenticated_host not in ALLOWED_HOSTS:
                raise AuditFailure("authenticated account host is not approved")
            checks["current_account_exact"] = True

            if (
                len(login_parts) != 2
                or login_parts[0] != APPROVED_USERNAME
                or login_parts[1].lower() not in ALLOWED_HOSTS
            ):
                raise AuditFailure("login identity does not match the approved account")
            checks["login_identity_matches_approved_account"] = True

            if database_name != APPROVED_DATABASE:
                raise AuditFailure("selected database is not approved")
            checks["approved_database_selected"] = True

            grantee = f"'{APPROVED_USERNAME}'@'{authenticated_host}'"
            stage = "schema_privileges"
            schema_rows = connection.execute(
                text(
                    "SELECT TABLE_SCHEMA, PRIVILEGE_TYPE, IS_GRANTABLE "
                    "FROM information_schema.SCHEMA_PRIVILEGES WHERE GRANTEE = :grantee"
                ),
                {"grantee": grantee},
            ).all()
            stage = "table_privileges"
            table_rows = connection.execute(
                text(
                    "SELECT TABLE_SCHEMA, TABLE_NAME, PRIVILEGE_TYPE, IS_GRANTABLE "
                    "FROM information_schema.TABLE_PRIVILEGES WHERE GRANTEE = :grantee"
                ),
                {"grantee": grantee},
            ).all()
            stage = "column_privileges"
            column_rows = connection.execute(
                text(
                    "SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, PRIVILEGE_TYPE, IS_GRANTABLE "
                    "FROM information_schema.COLUMN_PRIVILEGES WHERE GRANTEE = :grantee"
                ),
                {"grantee": grantee},
            ).all()
            stage = "routine_privileges"
            # MySQL 8.0 has no INFORMATION_SCHEMA.ROUTINE_PRIVILEGES table.
            # Routine grants are checked from SHOW GRANTS below and rejected
            # explicitly; no additional mysql-system-table permission is needed.
            stage = "global_privileges"
            global_rows = connection.execute(
                text(
                    "SELECT PRIVILEGE_TYPE, IS_GRANTABLE "
                    "FROM information_schema.USER_PRIVILEGES WHERE GRANTEE = :grantee"
                ),
                {"grantee": grantee},
            ).all()

            stage = "applicable_roles"
            role_rows = connection.execute(
                text(
                    "SELECT ROLE_NAME, ROLE_HOST FROM information_schema.APPLICABLE_ROLES "
                    "WHERE GRANTEE = :grantee"
                ),
                {"grantee": grantee},
            ).all()
            stage = "enabled_roles"
            enabled_role_rows = connection.execute(
                text("SELECT ROLE_NAME, ROLE_HOST FROM information_schema.ENABLED_ROLES")
            ).all()
            role_grant_rows = []
            if role_rows:
                stage = "role_grants_using_assigned_roles"
                role_clause = ", ".join(
                    f"{_quote_identifier(role_name, identifier_preparer)}@"
                    f"{_quote_identifier(role_host, identifier_preparer)}"
                    for role_name, role_host in role_rows
                )
                role_grant_rows = connection.exec_driver_sql(
                    f"SHOW GRANTS FOR CURRENT_USER() USING {role_clause}"
                ).all()

            # Read-only inspection of both proxy grants held by this account and
            # mappings that can proxy into this account. Visibility is mandatory.
            stage = "proxy_mappings"
            proxy_rows = connection.execute(
                text(
                    "SELECT User, Host, Proxied_user, Proxied_host, With_grant "
                    "FROM mysql.proxies_priv WHERE "
                    "User = :user OR Proxied_user = :user"
                ),
                {"user": APPROVED_USERNAME},
            ).all()

            stage = "show_grants_current_session"
            show_grant_rows = connection.exec_driver_sql("SHOW GRANTS").all()
            stage = "show_grants_authenticated_account"
            direct_grant_rows = connection.exec_driver_sql(
                "SHOW GRANTS FOR CURRENT_USER()"
            ).all()

            stage = "visible_schemas"
            schema_names = [
                str(row[0])
                for row in connection.execute(
                    text("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA")
                ).all()
            ]

            checks["privilege_metadata_readable"] = True
            checks["roles_inspected"] = True
            checks["proxy_mappings_inspected"] = True

        stage = "metadata_validation"
        partial_revokes_enabled = _normalize_partial_revokes(partial_revokes)
        schema_privileges: dict[str, set[str]] = defaultdict(set)
        schema_grantable: set[str] = set()
        for target, privilege, grantable in schema_rows:
            target = str(target)
            schema_privileges[target].add(_privilege_name(privilege))
            if str(grantable).upper() == "YES":
                schema_grantable.add(target)

        table_privileges: dict[tuple[str, str], set[str]] = defaultdict(set)
        table_grantable: set[tuple[str, str]] = set()
        for target_db, table_name, privilege, grantable in table_rows:
            key = (str(target_db), str(table_name))
            table_privileges[key].add(_privilege_name(privilege))
            if str(grantable).upper() == "YES":
                table_grantable.add(key)

        global_privileges = {_privilege_name(row[0]) for row in global_rows}
        global_grantable = any(str(row[1]).upper() == "YES" for row in global_rows)
        column_privilege_count = len(column_rows)
        column_grants = [
            {
                "database": str(row[0]),
                "table": str(row[1]),
                "column": str(row[2]),
                "privilege": _privilege_name(row[3]),
                "grant_option": str(row[4]).upper() == "YES",
            }
            for row in column_rows
        ]
        schema_targets = []
        for pattern, privileges in sorted(schema_privileges.items()):
            visible_matches = sorted(
                name
                for name in schema_names
                if _pattern_matches(pattern, name, partial_revokes_enabled)
            )
            schema_targets.append(
                {
                    "database_pattern": pattern,
                    "privileges": sorted(privileges),
                    "grant_option": pattern in schema_grantable,
                    "wildcard_scope": _has_active_wildcard(
                        pattern, partial_revokes_enabled
                    ),
                    "visible_matching_databases": visible_matches,
                    "matches_approved_database": _pattern_matches(
                        pattern, APPROVED_DATABASE, partial_revokes_enabled
                    ),
                    "matches_mybroker_db": _pattern_matches(
                        pattern, "mybroker_db", partial_revokes_enabled
                    ),
                }
            )

        overlapping_schema_patterns = []
        for visible_name in schema_names:
            matching_patterns = [
                pattern
                for pattern in sorted(schema_privileges)
                if _pattern_matches(pattern, visible_name, partial_revokes_enabled)
            ]
            if len(matching_patterns) > 1:
                overlapping_schema_patterns.append(
                    {"visible_database": visible_name, "patterns": matching_patterns}
                )

        grant_categories: dict[str, int] = defaultdict(int)
        unsupported_grants = False
        for row in (*show_grant_rows, *direct_grant_rows):
            category = _grant_row_category(str(row[0]))
            grant_categories[category] += 1
            if category == "unsupported grant format":
                unsupported_grants = True
        schema_grants_present = grant_categories.get("schema grant", 0) > 0
        # Visible schema names cannot prove a schema grant's full scope. Also
        # treat any unsupported grant row as incomplete scope metadata.
        schema_scope_analysis_complete = (
            not schema_privileges
            and not schema_grants_present
            and not unsupported_grants
        )
        role_grant_categories: dict[str, int] = defaultdict(int)
        for row in role_grant_rows:
            role_grant_categories[_grant_row_category(str(row[0]))] += 1

        role_count = len(role_rows)
        enabled_role_count = len(enabled_role_rows)
        mandatory_roles_present = bool(str(mandatory_roles).strip())
        if not isinstance(current_roles, str) or not current_roles:
            raise AuditFailure("current role metadata is unsupported")
        active_roles_present = current_roles != "NONE"
        proxy_count = len(proxy_rows)
        role_assignments_present = grant_categories.get("role assignment", 0) > 0
        proxy_grants_present = grant_categories.get("proxy grant", 0) > 0
        routine_grants_present = grant_categories.get("routine grant", 0) > 0
        global_grants_present = grant_categories.get("global grant", 0) > 0

        expected_tables = {
            (APPROVED_DATABASE, table): privileges
            for table, privileges in REQUIRED_TABLE_PRIVILEGES.items()
        }
        table_privileges_match = (
            table_privileges == expected_tables
            and not table_grantable
            and not schema_privileges
            and not column_privilege_count
            and not routine_grants_present
            and global_privileges <= {"USAGE"}
            and not global_grantable
        )
        no_unapproved_paths = (
            not schema_privileges
            and not column_privilege_count
            and global_privileges <= {"USAGE"}
            and not global_grantable
            and role_count == 0
            and enabled_role_count == 0
            and not mandatory_roles_present
            and not active_roles_present
            and not role_assignments_present
            and not routine_grants_present
            and proxy_count == 0
            and not proxy_grants_present
            and not schema_grants_present
            and not global_grants_present
            and not unsupported_grants
            and schema_scope_analysis_complete
        )
        checks["table_privileges_match_allowlist"] = table_privileges_match
        checks["no_unapproved_privilege_paths"] = no_unapproved_paths
        passed = all(checks.values())

        details = {
            "identity_checks": {
                "current_account_exact": checks["current_account_exact"],
                "login_identity_matches_approved_account": checks[
                    "login_identity_matches_approved_account"
                ],
                "effective_host_class": "loopback",
            },
            "database": str(database_name),
            "partial_revokes_enabled": partial_revokes_enabled,
            "mandatory_roles_present": mandatory_roles_present,
            "active_roles_present": active_roles_present,
            "applicable_role_count": role_count,
            "enabled_role_count": enabled_role_count,
            "proxy_mapping_count": proxy_count,
            "role_assignments_present": role_assignments_present,
            "routine_grants_present": routine_grants_present,
            "proxy_grants_present": proxy_grants_present,
            "grant_categories": dict(sorted(grant_categories.items())),
            "role_grant_categories": dict(sorted(role_grant_categories.items())),
            "global_privileges": sorted(global_privileges),
            "schema_grants": schema_targets,
            "table_grants": [
                {
                    "database": database,
                    "table": table,
                    "privileges": sorted(privileges),
                }
                for (database, table), privileges in sorted(table_privileges.items())
            ],
            "column_privilege_count": column_privilege_count,
            "column_grants": column_grants,
            "overlapping_schema_patterns_for_visible_databases": overlapping_schema_patterns,
            "schema_scope_analysis_complete": schema_scope_analysis_complete,
            "wildcard_schema_patterns_require_manual_overlap_review": any(
                item["wildcard_scope"] for item in schema_targets
            ),
        }
        _emit("PASS" if passed else "FAIL", checks, details, 0 if passed else 1)
    except AuditFailure:
        _emit("FAIL", checks, {"failure_category": "identity_or_privilege_validation"}, 1)
    except Exception as error:
        _emit(
            "FAIL",
            checks,
            {
                "failure_stage": stage,
                "failure_category": _database_error_category(error),
            },
            1,
        )
    finally:
        if engine is not None:
            try:
                engine.dispose()
            except Exception:
                pass


if __name__ == "__main__":
    main()
