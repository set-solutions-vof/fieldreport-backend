from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role = postgresql.ENUM("admin", "inspector", name="user_role", create_type=False)
    report_status = postgresql.ENUM(
        "generating",
        "draft",
        "approved",
        "failed",
        name="report_status",
        create_type=False,
    )
    report_evidence_type = postgresql.ENUM(
        "transcription_segment",
        "image_analysis",
        name="report_evidence_type",
        create_type=False,
    )
    confidence_level_enum = postgresql.ENUM(
        "high",
        "medium",
        "low",
        name="confidence_level_enum",
        create_type=False,
    )
    render_type_enum = postgresql.ENUM(
        "text_block",
        "key_value_table",
        "measurement_table",
        "photo_grid",
        name="render_type_enum",
        create_type=False,
    )
    template_analysis_status_enum = postgresql.ENUM(
        "queued",
        "processing",
        "pending_review",
        "active",
        "failed",
        name="template_analysis_status_enum",
        create_type=False,
    )

    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    report_status.create(bind, checkfirst=True)
    report_evidence_type.create(bind, checkfirst=True)
    confidence_level_enum.create(bind, checkfirst=True)
    render_type_enum.create(bind, checkfirst=True)
    template_analysis_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "company",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("industry", sa.String(), nullable=False),
        sa.Column("current_template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("phone_number", sa.String(), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("structure", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("logo_url", sa.String(), nullable=False),
        sa.Column("primary_color", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key(
        "fk_company_current_template_id",
        "company",
        "templates",
        ["current_template_id"],
        ["id"],
    )
    op.create_table(
        "inspections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inspector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_name", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("investigation_type", sa.Text(), nullable=False),
        sa.Column("client_type", sa.Text(), nullable=False),
        sa.Column("extra_context", sa.Text(), nullable=False),
        sa.Column("inspection_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.ForeignKeyConstraint(["inspector_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "inspection_audio_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inspection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("original_file_name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "inspection_photo_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inspection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("original_file_name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "transcriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inspection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "image_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inspection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=True),
        sa.Column("analysis_text", sa.Text(), nullable=False),
        sa.Column("geotag_lat", sa.Float(), nullable=True),
        sa.Column("geotag_lng", sa.Float(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "transcription_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transcription_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inspection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.Column("start_seconds", sa.Float(), nullable=False),
        sa.Column("end_seconds", sa.Float(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"]),
        sa.ForeignKeyConstraint(["transcription_id"], ["transcriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inspection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", report_status, nullable=False),
        sa.Column("pdf_storage_key", sa.String(), nullable=True),
        sa.Column("sent_to_email", sa.String(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "report_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_id", sa.String(), nullable=False),
        sa.Column("section_order", sa.Integer(), nullable=False),
        sa.Column("render_type", render_type_enum, nullable=False, server_default="text_block"),
        sa.Column("generated_content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reviewed_content", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("edit_distance", sa.Integer(), nullable=True),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confidence_level", confidence_level_enum, nullable=False, server_default="high"),
        sa.Column("confidence_score", sa.Numeric(3, 2), nullable=False, server_default="0.95"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "report_section_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_section_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_type", report_evidence_type, nullable=False),
        sa.Column("transcription_segment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("image_analysis_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(transcription_segment_id IS NOT NULL) <> (image_analysis_id IS NOT NULL)",
            name="ck_report_section_evidence_exactly_one_source",
        ),
        sa.ForeignKeyConstraint(["image_analysis_id"], ["image_analyses.id"]),
        sa.ForeignKeyConstraint(["report_section_id"], ["report_sections.id"]),
        sa.ForeignKeyConstraint(["transcription_segment_id"], ["transcription_segments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "template_analysis_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", template_analysis_status_enum, nullable=False),
        sa.Column("source_reports_count", sa.Integer(), nullable=False),
        sa.Column("structure", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "template_analysis_job_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_file_name", sa.String(), nullable=False),
        sa.Column("stored_file_path", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["template_analysis_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
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
    op.drop_table("template_analysis_job_files")
    op.drop_table("template_analysis_jobs")
    op.drop_table("report_section_evidence")
    op.drop_table("report_sections")
    op.drop_table("reports")
    op.drop_table("transcription_segments")
    op.drop_table("image_analyses")
    op.drop_table("transcriptions")
    op.drop_table("inspection_photo_files")
    op.drop_table("inspection_audio_files")
    op.drop_table("inspections")
    op.drop_constraint("fk_company_current_template_id", "company", type_="foreignkey")
    op.drop_table("templates")
    op.drop_table("users")
    op.drop_table("company")

    bind = op.get_bind()
    postgresql.ENUM(
        "queued",
        "processing",
        "pending_review",
        "active",
        "failed",
        name="template_analysis_status_enum",
    ).drop(bind, checkfirst=True)
    postgresql.ENUM(
        "text_block",
        "key_value_table",
        "measurement_table",
        "photo_grid",
        name="render_type_enum",
    ).drop(bind, checkfirst=True)
    postgresql.ENUM("high", "medium", "low", name="confidence_level_enum").drop(
        bind, checkfirst=True
    )
    postgresql.ENUM(
        "transcription_segment",
        "image_analysis",
        name="report_evidence_type",
    ).drop(bind, checkfirst=True)
    postgresql.ENUM(
        "generating",
        "draft",
        "approved",
        "failed",
        name="report_status",
    ).drop(bind, checkfirst=True)
    postgresql.ENUM("admin", "inspector", name="user_role").drop(bind, checkfirst=True)
