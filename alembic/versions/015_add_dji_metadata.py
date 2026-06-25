from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE image_analyses ADD COLUMN IF NOT EXISTS dji_metadata JSONB")


def downgrade() -> None:
    op.execute("ALTER TABLE image_analyses DROP COLUMN IF EXISTS dji_metadata")
