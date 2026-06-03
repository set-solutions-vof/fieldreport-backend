from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role = postgresql.ENUM("admin", "inspector", name="user_role", create_type=False)

    op.add_column("company", sa.Column("logo_url", sa.String(), nullable=True))
    op.add_column("company", sa.Column("primary_color", sa.String(length=7), nullable=True))
    op.add_column(
        "company",
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("is_accepted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )


def downgrade() -> None:
    op.drop_table("invites")
    op.drop_column("company", "onboarding_completed")
    op.drop_column("company", "primary_color")
    op.drop_column("company", "logo_url")
