import sqlalchemy as sa
from sqlalchemy import text

from src.db.connection import get_pool
from src.db.report_mapper import (
    map_report_detail,
    map_report_pipeline_context,
    map_report_sections,
    map_report_summary,
    map_stored_image_analysis,
    map_stored_transcription_segment,
)
from src.db.tables import (
    image_analyses,
    inspections,
    report_section_evidence,
    report_sections,
    reports,
    transcription_segments,
    users,
)
from src.exceptions import ReportNotFound
from src.models.reports.pipeline import (
    ReportPipelineContext,
    StoredImageAnalysis,
    StoredTranscriptionSegment,
)
from src.models.reports.report import (
    ReportDetail,
    ReportSection,
    ReportSummary,
)


def _report_section_content(column):
    return column[0].astext


def _report_section_detail_columns(include_timeline: bool):
    columns = [
        report_sections.c.id,
        report_sections.c.section_id,
        report_sections.c.label,
        report_sections.c.fields,
        report_sections.c.groups,
        report_sections.c.section_order,
        report_sections.c.render_type,
        _report_section_content(report_sections.c.generated_content).label("generated_content"),
        _report_section_content(report_sections.c.reviewed_content).label("reviewed_content"),
        report_sections.c.approved,
        report_sections.c.confidence_level,
        report_sections.c.confidence_score,
        report_section_evidence.c.evidence_type.label("evidence_type"),
        transcription_segments.c.id.label("transcription_segment_id"),
        transcription_segments.c.start_seconds.label("start_seconds"),
        transcription_segments.c.end_seconds.label("end_seconds"),
        transcription_segments.c.text.label("transcription_text"),
        image_analyses.c.id.label("image_analysis_id"),
        image_analyses.c.storage_key.label("image_storage_key"),
        image_analyses.c.captured_at.label("captured_at"),
        image_analyses.c.analysis_text.label("image_analysis_text"),
    ]

    if include_timeline:
        columns.append(
            sa.case(
                (
                    report_section_evidence.c.evidence_type == "transcription_segment",
                    transcription_segments.c.start_seconds,
                ),
                (
                    report_section_evidence.c.evidence_type == "image_analysis",
                    sa.cast(
                        sa.extract(
                            "epoch",
                            sa.func.coalesce(
                                image_analyses.c.captured_at,
                                image_analyses.c.created_at,
                            )
                            - inspections.c.created_at,
                        ),
                        sa.Float,
                    ),
                ),
            ).label("timeline_seconds")
        )

    return columns


def _report_sections_join():
    return (
        report_sections.join(reports, reports.c.id == report_sections.c.report_id)
        .join(inspections, inspections.c.id == reports.c.inspection_id)
        .join(
            report_section_evidence,
            report_section_evidence.c.report_section_id == report_sections.c.id,
        )
        .outerjoin(
            transcription_segments,
            transcription_segments.c.id == report_section_evidence.c.transcription_segment_id,
        )
        .outerjoin(
            image_analyses,
            image_analyses.c.id == report_section_evidence.c.image_analysis_id,
        )
    )


async def list_report_summaries_by_company_id(company_id: str) -> list[ReportSummary]:
    statement = (
        sa.select(
            reports.c.id,
            reports.c.company_id,
            reports.c.status,
            inspections.c["metadata"],
            sa.cast(inspections.c.inspection_date, sa.DateTime()).label("inspection_date"),
            users.c.name.label("inspector_name"),
        )
        .select_from(
            reports.join(inspections, inspections.c.id == reports.c.inspection_id).join(
                users, users.c.id == inspections.c.inspector_id
            )
        )
        .where(reports.c.company_id == company_id)
        .order_by(reports.c.created_at.desc())
    )

    async with get_pool().acquire() as connection:
        result = await connection.execute(statement)
        rows = result.mappings().all()

    return [map_report_summary(row) for row in rows]


async def get_report_by_id(report_id: str, company_id: str) -> ReportDetail:
    statement = (
        sa.select(
            reports.c.id,
            reports.c.status,
            reports.c.updated_at,
            inspections.c["metadata"],
            sa.cast(inspections.c.inspection_date, sa.DateTime()).label("inspection_date"),
            users.c.name.label("inspector_name"),
        )
        .select_from(
            reports.join(inspections, inspections.c.id == reports.c.inspection_id).join(
                users, users.c.id == inspections.c.inspector_id
            )
        )
        .where(
            reports.c.id == report_id,
            reports.c.company_id == company_id,
        )
    )

    async with get_pool().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().first()

    if row is None:
        raise ReportNotFound(report_id)

    return map_report_detail(row)


async def fetch_report_section_rows(report_id: str, company_id: str) -> list:
    statement = (
        sa.select(*_report_section_detail_columns(include_timeline=True))
        .select_from(_report_sections_join())
        .where(
            report_sections.c.report_id == report_id,
            reports.c.company_id == company_id,
        )
        .order_by(
            report_sections.c.section_order.asc(),
            report_section_evidence.c.created_at.asc(),
        )
    )

    async with get_pool().acquire() as connection:
        result = await connection.execute(statement)
        return result.mappings().all()


async def update_report_section(
    report_id: str,
    section_id: str,
    company_id: str,
    reviewed_content: str | None,
    approved: bool | None,
) -> ReportSection:
    async with get_pool().acquire() as connection:
        values: dict[str, object] = {}

        if reviewed_content is not None:
            values["reviewed_content"] = [reviewed_content]

        if approved is not None:
            values["approved"] = approved

        if values:
            values["updated_at"] = sa.func.now()
            section_statement = (
                report_sections.update()
                .where(
                    reports.c.id == report_sections.c.report_id,
                    report_sections.c.id == section_id,
                    report_sections.c.report_id == report_id,
                    reports.c.company_id == company_id,
                )
                .values(**values)
                .returning(report_sections.c.id)
            )
        else:
            section_statement = (
                sa.select(report_sections.c.id)
                .select_from(
                    report_sections.join(reports, reports.c.id == report_sections.c.report_id)
                )
                .where(
                    report_sections.c.id == section_id,
                    report_sections.c.report_id == report_id,
                    reports.c.company_id == company_id,
                )
            )

        section_result = await connection.execute(section_statement)
        section_row = section_result.mappings().first()

        if section_row is None:
            raise ReportNotFound(report_id)

        rows_statement = (
            sa.select(*_report_section_detail_columns(include_timeline=False))
            .select_from(_report_sections_join())
            .where(report_sections.c.id == section_row["id"])
            .order_by(report_section_evidence.c.created_at.asc())
        )
        rows_result = await connection.execute(rows_statement)
        rows = rows_result.mappings().all()

    return map_report_sections(rows)[0]


async def claim_next_audio_pipeline_report() -> dict | None:
    statement = text(
        """
        WITH next_report AS (
            SELECT id
            FROM reports
            WHERE status = 'generating'::report_status
            ORDER BY created_at ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        )
        SELECT id, inspection_id, company_id, template_id
        FROM reports
        WHERE id IN (SELECT id FROM next_report)
        """
    )

    async with get_pool().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().first()

    return dict(row) if row is not None else None


async def get_report_for_pipeline(report_id: str) -> ReportPipelineContext:
    statement = (
        sa.select(
            reports.c.id,
            reports.c.inspection_id,
            reports.c.company_id,
            reports.c.template_id,
            reports.c.status,
            inspections.c.extra_context,
            inspections.c["metadata"],
        )
        .select_from(reports.join(inspections, inspections.c.id == reports.c.inspection_id))
        .where(reports.c.id == report_id)
    )

    async with get_pool().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().one()

    return map_report_pipeline_context(row)


async def set_report_status(report_id: str, status: str) -> None:
    statement = (
        reports.update()
        .where(reports.c.id == report_id)
        .values(status=status, updated_at=sa.func.now())
    )

    async with get_pool().acquire() as connection:
        await connection.execute(statement)


async def fetch_transcription_segments_for_inspection(
    inspection_id: str,
) -> list[StoredTranscriptionSegment]:
    statement = (
        sa.select(
            transcription_segments.c.id,
            transcription_segments.c.transcription_id,
            transcription_segments.c.inspection_id,
            transcription_segments.c.segment_index,
            transcription_segments.c.start_seconds,
            transcription_segments.c.end_seconds,
            transcription_segments.c.text,
            transcription_segments.c.created_at,
        )
        .where(transcription_segments.c.inspection_id == inspection_id)
        .order_by(
            transcription_segments.c.transcription_id.asc(),
            transcription_segments.c.segment_index.asc(),
        )
    )

    async with get_pool().acquire() as connection:
        result = await connection.execute(statement)
        rows = result.mappings().all()

    return [map_stored_transcription_segment(row) for row in rows]


async def fetch_image_analyses_for_inspection(inspection_id: str) -> list[StoredImageAnalysis]:
    statement = (
        sa.select(
            image_analyses.c.id,
            image_analyses.c.inspection_id,
            image_analyses.c.company_id,
            image_analyses.c.storage_key,
            image_analyses.c.analysis_text,
            image_analyses.c.captured_at,
            image_analyses.c.created_at,
        )
        .where(image_analyses.c.inspection_id == inspection_id)
        .order_by(image_analyses.c.created_at.asc())
    )

    async with get_pool().acquire() as connection:
        result = await connection.execute(statement)
        rows = result.mappings().all()

    return [map_stored_image_analysis(row) for row in rows]
