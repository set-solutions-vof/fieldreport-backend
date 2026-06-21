from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE invites ADD COLUMN IF NOT EXISTS first_name VARCHAR NOT NULL DEFAULT ''"
    )
    op.execute("ALTER TABLE invites ADD COLUMN IF NOT EXISTS last_name VARCHAR NOT NULL DEFAULT ''")


def downgrade() -> None:
    op.drop_column("invites", "last_name")
    op.drop_column("invites", "first_name")
