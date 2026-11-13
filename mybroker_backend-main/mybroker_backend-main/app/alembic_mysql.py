"""MySQL-specific Alembic implementation customizations."""

from alembic.ddl.mysql import MySQLImpl
from sqlalchemy import Column, MetaData, PrimaryKeyConstraint, String, Table


class MySQLLongVersionImpl(MySQLImpl):
    """Allow migration identifiers longer than Alembic's 32 character default."""

    # Alembic's implementation metaclass registers this class under the same
    # dialect key, replacing MySQLImpl for contexts configured afterward.
    __dialect__ = "mysql"

    def version_table_impl(
        self,
        *,
        version_table: str,
        version_table_schema: str | None,
        version_table_pk: bool,
        **kw: object,
    ) -> Table:
        table = Table(
            version_table,
            MetaData(),
            Column("version_num", String(128), nullable=False),
            schema=version_table_schema,
        )
        if version_table_pk:
            table.append_constraint(
                PrimaryKeyConstraint("version_num", name=f"{version_table}_pkc")
            )
        return table


# Importing this module in alembic/env.py installs the override before Alembic
# configures either an online or offline migration context.
