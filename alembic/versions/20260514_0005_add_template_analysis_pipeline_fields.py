from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260514_0005"
down_revision = "20260514_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE template_analysis_status_enum ADD VALUE IF NOT EXISTS 'queued'")
    op.execute("ALTER TYPE template_analysis_status_enum ADD VALUE IF NOT EXISTS 'processing'")
    op.execute("ALTER TYPE template_analysis_status_enum ADD VALUE IF NOT EXISTS 'failed'")
    op.execute(
        """
        UPDATE template_analysis_jobs
        SET status = 'queued'::template_analysis_status_enum
        WHERE status = 'extracting'::template_analysis_status_enum
        """
    )
    op.add_column(
        "template_analysis_jobs",
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "template_analysis_jobs",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "template_analysis_jobs",
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "template_analysis_job_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("storage_path", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["template_analysis_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("template_analysis_job_files")
    op.drop_column("template_analysis_jobs", "finished_at")
    op.drop_column("template_analysis_jobs", "started_at")
    op.drop_column("template_analysis_jobs", "error_message")
