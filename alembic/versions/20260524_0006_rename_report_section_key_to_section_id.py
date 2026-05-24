from __future__ import annotations

from alembic import op

revision = "20260524_0006"
down_revision = "20260514_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("report_sections", "section_key", new_column_name="section_id")


def downgrade() -> None:
    op.alter_column("report_sections", "section_id", new_column_name="section_key")
