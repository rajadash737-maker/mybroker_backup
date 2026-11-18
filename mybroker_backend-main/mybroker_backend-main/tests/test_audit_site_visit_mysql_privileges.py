import pytest

from scripts.audit_site_visit_mysql_privileges import _grant_row_category


@pytest.mark.parametrize(
    ("grant", "expected"),
    [
        (
            "GRANT EXECUTE ON PROCEDURE app_db.refresh_cache TO 'audit_user'@'localhost'",
            "routine grant",
        ),
        (
            "GRANT EXECUTE ON FUNCTION app_db.normalize_code TO 'audit_user'@'localhost'",
            "routine grant",
        ),
        (
            "GRANT EXECUTE ON PROCEDURE app_db.refresh_cache TO 'audit_user'@'localhost' "
            "WITH GRANT OPTION",
            "routine grant",
        ),
        (
            "GRANT EXECUTE ON FUNCTION app_db.normalize_code TO 'audit_user'@'localhost' "
            "WITH GRANT OPTION",
            "routine grant",
        ),
        (
            "GRANT EXECUTE ON PROCEDURE `app-db`.`refresh cache` "
            "TO 'audit_user'@'localhost'",
            "routine grant",
        ),
        (
            "GRANT EXECUTE ON FUNCTION `app-db`.`normalize code` "
            "TO 'audit_user'@'localhost'",
            "routine grant",
        ),
        (
            "GRANT EXECUTE ON PROCEDURE `app-db`.`refresh cache` "
            "TO 'audit_role'@'%' WITH GRANT OPTION",
            "routine grant",
        ),
        (
            "GRANT SELECT ON `app-db`.`listing` TO 'audit_user'@'localhost' "
            "WITH GRANT OPTION",
            "grant option",
        ),
    ],
)
def test_grant_row_category_classifies_routine_and_grant_option_rows(grant, expected):
    assert _grant_row_category(grant) == expected
