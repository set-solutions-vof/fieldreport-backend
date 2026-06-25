"""add panel_location_key to image_analyses

Revision ID: 017
Revises: 016
Create Date: 2026-06-25
"""

from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE image_analyses ADD COLUMN IF NOT EXISTS panel_location_key TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE image_analyses DROP COLUMN IF EXISTS panel_location_key")
