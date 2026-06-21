from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE templates
        ADD COLUMN IF NOT EXISTS source_reports_count INTEGER NOT NULL DEFAULT 0
        """
    )
    op.execute("ALTER TYPE template_analysis_status_enum ADD VALUE IF NOT EXISTS 'completed'")


def downgrade() -> None:
    op.drop_column("templates", "source_reports_count")
