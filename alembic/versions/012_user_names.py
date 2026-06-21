import sqlalchemy as sa

from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name VARCHAR NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR NOT NULL DEFAULT ''")
    op.execute(
        """
        UPDATE users
        SET
            first_name = split_part(trim(name), ' ', 1),
            last_name = CASE
                WHEN strpos(trim(name), ' ') > 0
                THEN trim(substring(trim(name) FROM strpos(trim(name), ' ') + 1))
                ELSE ''
            END
        """
    )
    op.drop_column("users", "name")


def downgrade() -> None:
    op.add_column("users", sa.Column("name", sa.String(), nullable=False, server_default=""))
    op.execute(
        """
        UPDATE users
        SET name = trim(concat(first_name, ' ', last_name))
        """
    )
    op.alter_column("users", "name", server_default=None)
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
