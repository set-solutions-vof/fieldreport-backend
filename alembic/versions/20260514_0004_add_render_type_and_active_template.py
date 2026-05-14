from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260514_0004"
down_revision = "20260513_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    render_type_enum = postgresql.ENUM(
        "text_block",
        "key_value_table",
        "measurement_table",
        "photo_grid",
        name="render_type_enum",
        create_type=False,
    )
    template_analysis_status_enum = postgresql.ENUM(
        "extracting",
        "pending_review",
        "active",
        name="template_analysis_status_enum",
        create_type=False,
    )

    bind = op.get_bind()
    render_type_enum.create(bind, checkfirst=True)
    template_analysis_status_enum.create(bind, checkfirst=True)

    op.add_column(
        "company",
        sa.Column("active_template_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_company_active_template_id",
        "company",
        "templates",
        ["active_template_id"],
        ["id"],
    )
    op.add_column(
        "report_sections",
        sa.Column(
            "render_type",
            render_type_enum,
            nullable=False,
            server_default="text_block",
        ),
    )
    op.create_table(
        "template_analysis_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", template_analysis_status_enum, nullable=False),
        sa.Column("reports_count", sa.Integer(), nullable=False),
        sa.Column("structure", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "report_sections",
        sa.Column("ai_content", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.execute("UPDATE report_sections SET ai_content = to_jsonb(ARRAY[ai_draft])")
    op.alter_column("report_sections", "ai_content", nullable=False)
    op.drop_column("report_sections", "ai_draft")
    op.add_column(
        "report_sections",
        sa.Column("expert_content", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.execute(
        "UPDATE report_sections SET expert_content = to_jsonb(ARRAY[field_expert_content]) "
        "WHERE field_expert_content IS NOT NULL"
    )
    op.drop_column("report_sections", "field_expert_content")


def downgrade() -> None:
    op.drop_table("template_analysis_jobs")
    op.add_column("report_sections", sa.Column("field_expert_content", sa.Text(), nullable=True))
    op.execute(
        "UPDATE report_sections SET field_expert_content = expert_content ->> 0 "
        "WHERE expert_content IS NOT NULL"
    )
    op.add_column("report_sections", sa.Column("ai_draft", sa.Text(), nullable=True))
    op.execute("UPDATE report_sections SET ai_draft = ai_content ->> 0")
    op.alter_column("report_sections", "ai_draft", nullable=False)
    op.drop_column("report_sections", "expert_content")
    op.drop_column("report_sections", "ai_content")
    op.drop_column("report_sections", "render_type")
    op.drop_constraint("fk_company_active_template_id", "company", type_="foreignkey")
    op.drop_column("company", "active_template_id")

    bind = op.get_bind()
    postgresql.ENUM(
        "extracting",
        "pending_review",
        "active",
        name="template_analysis_status_enum",
    ).drop(bind, checkfirst=True)
    postgresql.ENUM(
        "text_block",
        "key_value_table",
        "measurement_table",
        "photo_grid",
        name="render_type_enum",
    ).drop(bind, checkfirst=True)
