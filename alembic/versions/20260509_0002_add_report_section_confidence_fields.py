from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260509_0002"
down_revision = "20260508_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    confidence_level_enum = postgresql.ENUM(
        "high",
        "medium",
        "low",
        name="confidence_level_enum",
        create_type=False,
    )

    bind = op.get_bind()
    confidence_level_enum.create(bind, checkfirst=True)

    op.add_column(
        "report_sections",
        sa.Column(
            "confidence_level",
            confidence_level_enum,
            nullable=False,
            server_default="high",
        ),
    )
    op.add_column(
        "report_sections",
        sa.Column(
            "confidence_score",
            sa.Numeric(3, 2),
            nullable=False,
            server_default="0.95",
        ),
    )


def downgrade() -> None:
    op.drop_column("report_sections", "confidence_score")
    op.drop_column("report_sections", "confidence_level")

    bind = op.get_bind()
    postgresql.ENUM(
        "high",
        "medium",
        "low",
        name="confidence_level_enum",
    ).drop(bind, checkfirst=True)
