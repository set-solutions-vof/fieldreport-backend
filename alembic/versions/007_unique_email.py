from __future__ import annotations

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_unique ON users (lower(email))")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS users_email_lower_unique")
