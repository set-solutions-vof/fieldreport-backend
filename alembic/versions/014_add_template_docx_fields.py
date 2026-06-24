from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE templates
        ADD COLUMN IF NOT EXISTS docx_storage_key TEXT,
        ADD COLUMN IF NOT EXISTS name TEXT,
        ADD COLUMN IF NOT EXISTS preview_pdf_storage_key TEXT
        """
    )
    op.execute("ALTER TYPE render_type_enum ADD VALUE IF NOT EXISTS 'repeating_group'")


def downgrade() -> None:
    op.execute("ALTER TABLE templates DROP COLUMN IF EXISTS docx_storage_key")
    op.execute("ALTER TABLE templates DROP COLUMN IF EXISTS name")
    op.execute("ALTER TABLE templates DROP COLUMN IF EXISTS preview_pdf_storage_key")
