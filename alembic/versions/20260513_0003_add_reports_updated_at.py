from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260513_0003"
down_revision = "20260509_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE reports SET updated_at = created_at")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_report_updated_at()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            UPDATE reports
            SET updated_at = NOW()
            WHERE id = NEW.report_id;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_report_sections_updated
        AFTER UPDATE ON report_sections
        FOR EACH ROW
        EXECUTE FUNCTION update_report_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_report_sections_updated ON report_sections")
    op.execute("DROP FUNCTION IF EXISTS update_report_updated_at")
    op.drop_column("reports", "updated_at")
