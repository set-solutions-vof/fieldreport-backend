from __future__ import annotations

from alembic import op

revision = "20260525_0008"
down_revision = "20260525_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            trigger_record record;
        BEGIN
            FOR trigger_record IN
                SELECT triggers.tgname
                FROM pg_trigger triggers
                JOIN pg_proc functions ON functions.oid = triggers.tgfoid
                WHERE triggers.tgrelid = 'report_sections'::regclass
                AND NOT triggers.tgisinternal
                AND functions.prosrc LIKE '%must have at least one source%'
            LOOP
                EXECUTE format(
                    'DROP TRIGGER IF EXISTS %I ON report_sections',
                    trigger_record.tgname
                );
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    pass
