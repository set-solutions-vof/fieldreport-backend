from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "report_sections",
        sa.Column("label", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "report_sections",
        sa.Column("fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "report_sections",
        sa.Column("groups", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.execute(
        "UPDATE report_sections SET label = INITCAP(REPLACE(section_id, '_', ' ')) WHERE label = ''"
    )


def downgrade() -> None:
    op.drop_column("report_sections", "groups")
    op.drop_column("report_sections", "fields")
    op.drop_column("report_sections", "label")
