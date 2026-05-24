import asyncpg

from src.db.connection import get_connection_url
from src.db.report_mapper import (
    map_report_detail,
    map_report_sections,
    map_report_summary,
)
from src.models.reports.report import (
    ReportDetail,
    ReportSection,
    ReportSummary,
)


async def list_report_summaries_by_company_id(company_id: str) -> list[ReportSummary]:
    connection = await asyncpg.connect(get_connection_url())

    try:
        rows = await connection.fetch(
            """
            SELECT
                reports.id,
                reports.company_id,
                reports.status,
                inspections.client_name,
                inspections.address,
                inspections.created_at AS inspection_date,
                users.name AS inspector_name
            FROM reports
            JOIN inspections ON inspections.id = reports.inspection_id
            JOIN users ON users.id = inspections.inspector_id
            WHERE reports.company_id = $1::uuid
            ORDER BY reports.created_at DESC
            """,
            company_id,
        )
    finally:
        await connection.close()

    return [map_report_summary(row) for row in rows]


async def get_report_by_id(report_id: str, company_id: str) -> ReportDetail:
    connection = await asyncpg.connect(get_connection_url())

    try:
        row = await connection.fetchrow(
            """
            SELECT
                reports.id,
                reports.status,
                reports.updated_at,
                inspections.client_name,
                inspections.address,
                inspections.created_at AS inspection_date,
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
    finally:
        await connection.close()

    return map_report_detail(row)


async def fetch_report_section_rows(report_id: str) -> list[asyncpg.Record]:
    connection = await asyncpg.connect(get_connection_url())

    try:
        return await connection.fetch(
            """
            SELECT
                report_sections.id,
                report_sections.section_id,
                report_sections.section_order,
                report_sections.render_type,
                report_sections.ai_content ->> 0 AS ai_draft,
                report_sections.expert_content ->> 0 AS field_expert_content,
                report_sections.is_approved,
                report_sections.confidence_level,
                report_sections.confidence_score,
                report_section_sources.source_type,
                transcription_segments.id AS transcription_segment_id,
                transcription_segments.start_seconds AS start_seconds,
                transcription_segments.end_seconds AS end_seconds,
                transcription_segments.text AS transcription_text,
                image_analyses.id AS image_analysis_id,
                image_analyses.captured_at AS captured_at,
                image_analyses.analysis_text AS image_analysis_text,
                CASE
                    WHEN report_section_sources.source_type = 'transcription_segment'
                        THEN transcription_segments.start_seconds
                    WHEN report_section_sources.source_type = 'image_analysis'
                        THEN EXTRACT(
                            EPOCH FROM (
                                COALESCE(image_analyses.captured_at, image_analyses.created_at)
                                - inspections.created_at
                            )
                        )::double precision
                END AS timeline_offset_seconds
            FROM report_sections
            JOIN reports ON reports.id = report_sections.report_id
            JOIN inspections ON inspections.id = reports.inspection_id
            JOIN report_section_sources
                ON report_section_sources.report_section_id = report_sections.id
            LEFT JOIN transcription_segments
                ON transcription_segments.id = report_section_sources.transcription_segment_id
            LEFT JOIN image_analyses
                ON image_analyses.id = report_section_sources.image_analysis_id
            WHERE report_sections.report_id = $1::uuid
            ORDER BY report_sections.section_order ASC, report_section_sources.created_at ASC
            """,
            report_id,
        )
    finally:
        await connection.close()


async def update_report_section(
    report_id: str,
    section_id: str,
    company_id: str,
    field_expert_content: str | None,
    is_approved: bool | None,
) -> ReportSection:
    connection = await asyncpg.connect(get_connection_url())

    try:
        values: list[object] = [report_id, section_id, company_id]
        assignments: list[str] = []

        if field_expert_content is not None:
            values.append(field_expert_content)
            assignments.append(f"expert_content = to_jsonb(ARRAY[${len(values)}::text])")

        if is_approved is not None:
            values.append(is_approved)
            assignments.append(f"is_approved = ${len(values)}::boolean")

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
                report_sections.section_order,
                report_sections.render_type,
                report_sections.ai_content ->> 0 AS ai_draft,
                report_sections.expert_content ->> 0 AS field_expert_content,
                report_sections.is_approved,
                report_sections.confidence_level,
                report_sections.confidence_score,
                report_section_sources.source_type,
                transcription_segments.start_seconds AS start_seconds,
                transcription_segments.end_seconds AS end_seconds,
                transcription_segments.text AS transcription_text,
                image_analyses.captured_at AS captured_at,
                image_analyses.analysis_text AS image_analysis_text
            FROM report_sections
            JOIN report_section_sources
                ON report_section_sources.report_section_id = report_sections.id
            LEFT JOIN transcription_segments
                ON transcription_segments.id = report_section_sources.transcription_segment_id
            LEFT JOIN image_analyses
                ON image_analyses.id = report_section_sources.image_analysis_id
            WHERE report_sections.id = $1::uuid
            ORDER BY report_section_sources.created_at ASC
            """,
            section_row["id"],
        )
    finally:
        await connection.close()

    return map_report_sections(rows)[0]
