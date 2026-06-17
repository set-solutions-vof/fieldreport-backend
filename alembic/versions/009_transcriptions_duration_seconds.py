from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS duration_seconds FLOAT NOT NULL DEFAULT 0"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE transcriptions DROP COLUMN IF EXISTS duration_seconds")
