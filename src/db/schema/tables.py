import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

metadata = sa.MetaData()

user_role = postgresql.ENUM("admin", "inspector", name="user_role", create_type=False)
report_status = postgresql.ENUM(
    "generating",
    "processing",
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

company = sa.Table(
    "company",
    metadata,
    sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
    sa.Column("name", sa.String(), nullable=False),
    sa.Column("industry", sa.String(), nullable=False),
    sa.Column("current_template_id", postgresql.UUID(as_uuid=False), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("logo_url", sa.String(), nullable=True),
    sa.Column("primary_color", sa.String(length=7), nullable=True),
    sa.Column("onboarding_completed", sa.Boolean(), nullable=False),
)

users = sa.Table(
    "users",
    metadata,
    sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
    sa.Column("company_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("email", sa.String(), nullable=False),
    sa.Column("password_hash", sa.String(), nullable=False),
    sa.Column("first_name", sa.String(), nullable=False),
    sa.Column("last_name", sa.String(), nullable=False),
    sa.Column("phone_number", sa.String(), nullable=False),
    sa.Column("role", user_role, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("last_sign_in_at", sa.DateTime(timezone=True), nullable=True),
)

templates = sa.Table(
    "templates",
    metadata,
    sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
    sa.Column("company_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("structure", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column("source_reports_count", sa.Integer(), nullable=False),
    sa.Column("logo_url", sa.String(), nullable=False),
    sa.Column("primary_color", sa.String(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

inspections = sa.Table(
    "inspections",
    metadata,
    sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
    sa.Column("company_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("inspector_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("template_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("extra_context", sa.Text(), nullable=False),
    sa.Column("inspection_date", sa.Date(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
)

inspection_audio_files = sa.Table(
    "inspection_audio_files",
    metadata,
    sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
    sa.Column("inspection_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("storage_key", sa.Text(), nullable=False),
    sa.Column("original_file_name", sa.Text(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

inspection_photo_files = sa.Table(
    "inspection_photo_files",
    metadata,
    sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
    sa.Column("inspection_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("storage_key", sa.Text(), nullable=False),
    sa.Column("original_file_name", sa.Text(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

transcriptions = sa.Table(
    "transcriptions",
    metadata,
    sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
    sa.Column("inspection_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("company_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("storage_key", sa.String(), nullable=True),
    sa.Column("raw_text", sa.Text(), nullable=False),
    sa.Column("duration_seconds", sa.Float(), nullable=False, server_default="0"),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

image_analyses = sa.Table(
    "image_analyses",
    metadata,
    sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
    sa.Column("inspection_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("company_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("storage_key", sa.String(), nullable=True),
    sa.Column("analysis_text", sa.Text(), nullable=False),
    sa.Column("geotag_lat", sa.Float(), nullable=True),
    sa.Column("geotag_lng", sa.Float(), nullable=True),
    sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

transcription_segments = sa.Table(
    "transcription_segments",
    metadata,
    sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
    sa.Column("transcription_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("inspection_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("segment_index", sa.Integer(), nullable=False),
    sa.Column("start_seconds", sa.Float(), nullable=False),
    sa.Column("end_seconds", sa.Float(), nullable=False),
    sa.Column("text", sa.Text(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

reports = sa.Table(
    "reports",
    metadata,
    sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
    sa.Column("inspection_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("company_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("template_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("status", report_status, nullable=False),
    sa.Column("pdf_storage_key", sa.String(), nullable=True),
    sa.Column("sent_to_email", sa.String(), nullable=True),
    sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
)

report_sections = sa.Table(
    "report_sections",
    metadata,
    sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
    sa.Column("report_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("company_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("section_id", sa.String(), nullable=False),
    sa.Column("section_order", sa.Integer(), nullable=False),
    sa.Column("render_type", render_type_enum, nullable=False),
    sa.Column("generated_content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column("reviewed_content", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column("edit_distance", sa.Integer(), nullable=True),
    sa.Column("approved", sa.Boolean(), nullable=False),
    sa.Column("confidence_level", confidence_level_enum, nullable=False),
    sa.Column("confidence_score", sa.Numeric(3, 2), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("label", sa.Text(), nullable=False),
    sa.Column("fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column("groups", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
)

report_section_evidence = sa.Table(
    "report_section_evidence",
    metadata,
    sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
    sa.Column("report_section_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("evidence_type", report_evidence_type, nullable=False),
    sa.Column("transcription_segment_id", postgresql.UUID(as_uuid=False), nullable=True),
    sa.Column("image_analysis_id", postgresql.UUID(as_uuid=False), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

template_analysis_jobs = sa.Table(
    "template_analysis_jobs",
    metadata,
    sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
    sa.Column("company_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("status", template_analysis_status_enum, nullable=False),
    sa.Column("source_reports_count", sa.Integer(), nullable=False),
    sa.Column("structure", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column("failure_message", sa.Text(), nullable=True),
    sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

template_analysis_job_files = sa.Table(
    "template_analysis_job_files",
    metadata,
    sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
    sa.Column("job_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("original_file_name", sa.String(), nullable=False),
    sa.Column("stored_file_path", sa.String(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

invites = sa.Table(
    "invites",
    metadata,
    sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
    sa.Column("company_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("email", sa.String(), nullable=False),
    sa.Column("first_name", sa.String(), nullable=False),
    sa.Column("last_name", sa.String(), nullable=False),
    sa.Column("role", user_role, nullable=False),
    sa.Column("token", sa.String(), nullable=False),
    sa.Column("is_accepted", sa.Boolean(), nullable=False),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

password_reset_tokens = sa.Table(
    "password_reset_tokens",
    metadata,
    sa.Column(
        "id",
        postgresql.UUID(as_uuid=False),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    ),
    sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
    sa.Column("token_hash", sa.String(), nullable=False, unique=True),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
)
