from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260525_0007"
down_revision = "20260524_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inspections",
        sa.Column(
            "investigation_type",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "inspections",
        sa.Column(
            "client_type",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "inspections",
        sa.Column(
            "extra_context",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "inspections",
        sa.Column(
            "inspection_date",
            sa.Date(),
            nullable=False,
            server_default=sa.text("CURRENT_DATE"),
        ),
    )
    op.create_table(
        "inspection_audio_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inspection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "inspection_photo_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inspection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("inspection_photo_files")
    op.drop_table("inspection_audio_files")
    op.drop_column("inspections", "inspection_date")
    op.drop_column("inspections", "extra_context")
    op.drop_column("inspections", "client_type")
    op.drop_column("inspections", "investigation_type")
