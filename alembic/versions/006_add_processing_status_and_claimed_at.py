from __future__ import annotations

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE report_status ADD VALUE IF NOT EXISTS 'processing'")
    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMP WITH TIME ZONE")


def downgrade() -> None:
    op.execute("ALTER TABLE reports DROP COLUMN IF EXISTS claimed_at")
