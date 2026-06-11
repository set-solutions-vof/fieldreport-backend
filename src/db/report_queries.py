from src.db.connection import get_pool
from src.db.report_mapper import (
    map_report_detail,
    map_report_pipeline_context,
    map_report_sections,
    map_report_summary,
    map_stored_image_analysis,
    map_stored_transcription_segment,
)
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


async def list_report_summaries_by_company_id(company_id: str) -> list[ReportSummary]:
    async with get_pool().acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT
                reports.id,
                reports.company_id,
                reports.status,
                inspections.metadata,
                inspections.inspection_date::timestamp AS inspection_date,
                users.name AS inspector_name
            FROM reports
            JOIN inspections ON inspections.id = reports.inspection_id
            JOIN users ON users.id = inspections.inspector_id
            WHERE reports.company_id = $1::uuid
            ORDER BY reports.created_at DESC
            """,
            company_id,
        )

    return [map_report_summary(row) for row in rows]


async def get_report_by_id(report_id: str, company_id: str) -> ReportDetail:
    async with get_pool().acquire() as connection:
        row = await connection.fetchrow(
            """
            SELECT
                reports.id,
                reports.status,
                reports.updated_at,
                inspections.metadata,
                inspections.inspection_date::timestamp AS inspection_date,
                users.name AS inspector_name
            FROM reports
            JOIN inspections ON inspections.id = reports.inspection_id
            JOIN users ON users.id = inspections.inspector_id
            WHERE reports.id = $1::uuid
            AND reports.company_id = $2::uuid
            """,
            report_id,
            company_id,
        )

    return map_report_detail(row)


async def fetch_report_section_rows(report_id: str, company_id: str) -> list:
    async with get_pool().acquire() as connection:
        return await connection.fetch(
            """
            SELECT
                report_sections.id,
                report_sections.section_id,
                report_sections.label,
                report_sections.fields,
                report_sections.groups,
                report_sections.section_order,
                report_sections.render_type,
                report_sections.generated_content ->> 0 AS generated_content,
                report_sections.reviewed_content ->> 0 AS reviewed_content,
                report_sections.approved AS approved,
                report_sections.confidence_level,
                report_sections.confidence_score,
                report_section_evidence.evidence_type AS evidence_type,
                transcription_segments.id AS transcription_segment_id,
                transcription_segments.start_seconds AS start_seconds,
                transcription_segments.end_seconds AS end_seconds,
                transcription_segments.text AS transcription_text,
                image_analyses.id AS image_analysis_id,
                image_analyses.storage_key AS image_storage_key,
                image_analyses.captured_at AS captured_at,
                image_analyses.analysis_text AS image_analysis_text,
                CASE
                    WHEN report_section_evidence.evidence_type = 'transcription_segment'
                        THEN transcription_segments.start_seconds
                    WHEN report_section_evidence.evidence_type = 'image_analysis'
                        THEN EXTRACT(
                            EPOCH FROM (
                                COALESCE(image_analyses.captured_at, image_analyses.created_at)
                                - inspections.created_at
                            )
                        )::double precision
                END AS timeline_seconds
            FROM report_sections
            JOIN reports ON reports.id = report_sections.report_id
            JOIN inspections ON inspections.id = reports.inspection_id
            JOIN report_section_evidence
                ON report_section_evidence.report_section_id = report_sections.id
            LEFT JOIN transcription_segments
                ON transcription_segments.id = report_section_evidence.transcription_segment_id
            LEFT JOIN image_analyses
                ON image_analyses.id = report_section_evidence.image_analysis_id
            WHERE report_sections.report_id = $1::uuid
            AND reports.company_id = $2::uuid
            ORDER BY report_sections.section_order ASC, report_section_evidence.created_at ASC
            """,
            report_id,
            company_id,
        )


async def update_report_section(
    report_id: str,
    section_id: str,
    company_id: str,
    reviewed_content: str | None,
    approved: bool | None,
) -> ReportSection:
    async with get_pool().acquire() as connection:
        values: list[object] = [report_id, section_id, company_id]
        assignments: list[str] = []

        if reviewed_content is not None:
            values.append(reviewed_content)
            assignments.append(f"reviewed_content = to_jsonb(ARRAY[${len(values)}::text])")

        if approved is not None:
            values.append(approved)
            assignments.append(f"approved = ${len(values)}::boolean")

        if assignments:
            assignments.append("updated_at = NOW()")
            section_row = await connection.fetchrow(
                f"""
                UPDATE report_sections
                SET {", ".join(assignments)}
                FROM reports
                WHERE reports.id = report_sections.report_id
                AND report_sections.id = $2::uuid
                AND report_sections.report_id = $1::uuid
                AND reports.company_id = $3::uuid
                RETURNING report_sections.id
                """,
                *values,
            )
        else:
            section_row = await connection.fetchrow(
                """
                SELECT report_sections.id
                FROM report_sections
                JOIN reports ON reports.id = report_sections.report_id
                WHERE report_sections.id = $2::uuid
                AND report_sections.report_id = $1::uuid
                AND reports.company_id = $3::uuid
                """,
                *values,
            )

        rows = await connection.fetch(
            """
            SELECT
                report_sections.id,
                report_sections.section_id,
                report_sections.label,
                report_sections.fields,
                report_sections.groups,
                report_sections.section_order,
                report_sections.render_type,
                report_sections.generated_content ->> 0 AS generated_content,
                report_sections.reviewed_content ->> 0 AS reviewed_content,
                report_sections.approved AS approved,
                report_sections.confidence_level,
                report_sections.confidence_score,
                report_section_evidence.evidence_type AS evidence_type,
                transcription_segments.start_seconds AS start_seconds,
                transcription_segments.end_seconds AS end_seconds,
                transcription_segments.text AS transcription_text,
                image_analyses.captured_at AS captured_at,
                image_analyses.analysis_text AS image_analysis_text
            FROM report_sections
            JOIN report_section_evidence
                ON report_section_evidence.report_section_id = report_sections.id
            LEFT JOIN transcription_segments
                ON transcription_segments.id = report_section_evidence.transcription_segment_id
            LEFT JOIN image_analyses
                ON image_analyses.id = report_section_evidence.image_analysis_id
            WHERE report_sections.id = $1::uuid
            ORDER BY report_section_evidence.created_at ASC
            """,
            section_row["id"],
        )

    return map_report_sections(rows)[0]


async def claim_next_audio_pipeline_report() -> dict | None:
    async with get_pool().acquire() as connection:
        row = await connection.fetchrow(
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

    return dict(row) if row is not None else None


async def get_report_for_pipeline(report_id: str) -> ReportPipelineContext:
    async with get_pool().acquire() as connection:
        row = await connection.fetchrow(
            """
            SELECT
                reports.id,
                reports.inspection_id,
                reports.company_id,
                reports.template_id,
                reports.status,
                inspections.extra_context,
                inspections.metadata
            FROM reports
            JOIN inspections ON inspections.id = reports.inspection_id
            WHERE reports.id = $1::uuid
            """,
            report_id,
        )

    return map_report_pipeline_context(row)


async def set_report_status(report_id: str, status: str) -> None:
    async with get_pool().acquire() as connection:
        await connection.execute(
            """
            UPDATE reports
            SET status = $2::report_status,
                updated_at = NOW()
            WHERE id = $1::uuid
            """,
            report_id,
            status,
        )


async def fetch_transcription_segments_for_inspection(
    inspection_id: str,
) -> list[StoredTranscriptionSegment]:
    async with get_pool().acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT
                id,
                transcription_id,
                inspection_id,
                segment_index,
                start_seconds,
                end_seconds,
                text,
                created_at
            FROM transcription_segments
            WHERE inspection_id = $1::uuid
            ORDER BY transcription_id ASC, segment_index ASC
            """,
            inspection_id,
        )

    return [map_stored_transcription_segment(row) for row in rows]


async def fetch_image_analyses_for_inspection(inspection_id: str) -> list[StoredImageAnalysis]:
    async with get_pool().acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT
                id,
                inspection_id,
                company_id,
                storage_key,
                analysis_text,
                captured_at,
                created_at
            FROM image_analyses
            WHERE inspection_id = $1::uuid
            ORDER BY created_at ASC
            """,
            inspection_id,
        )

    return [map_stored_image_analysis(row) for row in rows]
