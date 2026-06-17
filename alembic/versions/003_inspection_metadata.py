from __future__ import annotations

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE inspections ADD COLUMN metadata JSONB NOT NULL DEFAULT '{}'")


def downgrade() -> None:
    op.drop_column("inspections", "metadata")
