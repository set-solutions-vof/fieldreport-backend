from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE image_analyses ADD COLUMN IF NOT EXISTS thermal_metrics JSONB")


def downgrade() -> None:
    op.execute("ALTER TABLE image_analyses DROP COLUMN IF EXISTS thermal_metrics")
