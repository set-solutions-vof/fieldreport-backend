from __future__ import annotations

from alembic import op

revision = "20260526_0009"
down_revision = "20260525_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE template_analysis_jobs
        SET status = 'queued'::template_analysis_status_enum
        WHERE status = 'extracting'::template_analysis_status_enum
        """
    )
    op.execute(
        """
        ALTER TYPE template_analysis_status_enum RENAME TO template_analysis_status_enum_old
        """
    )
    op.execute(
        """
        CREATE TYPE template_analysis_status_enum AS ENUM (
            'queued',
            'processing',
            'pending_review',
            'active',
            'failed'
        )
        """
    )
    op.execute(
        """
        ALTER TABLE template_analysis_jobs
        ALTER COLUMN status TYPE template_analysis_status_enum
        USING status::text::template_analysis_status_enum
        """
    )
    op.execute("DROP TYPE template_analysis_status_enum_old")


def downgrade() -> None:
    op.execute(
        """
        ALTER TYPE template_analysis_status_enum RENAME TO template_analysis_status_enum_old
        """
    )
    op.execute(
        """
        CREATE TYPE template_analysis_status_enum AS ENUM (
            'queued',
            'processing',
            'extracting',
            'pending_review',
            'active',
            'failed'
        )
        """
    )
    op.execute(
        """
        ALTER TABLE template_analysis_jobs
        ALTER COLUMN status TYPE template_analysis_status_enum
        USING status::text::template_analysis_status_enum
        """
    )
    op.execute("DROP TYPE template_analysis_status_enum_old")
