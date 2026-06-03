from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("inspections", "client_name")
    op.drop_column("inspections", "address")
    op.drop_column("inspections", "investigation_type")
    op.drop_column("inspections", "client_type")


def downgrade() -> None:
    op.add_column(
        "inspections",
        sa.Column("client_type", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "inspections",
        sa.Column("investigation_type", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "inspections",
        sa.Column("address", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "inspections",
        sa.Column("client_name", sa.String(), nullable=False, server_default=""),
    )
