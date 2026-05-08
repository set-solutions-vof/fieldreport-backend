import asyncpg

from src.config import settings
from src.models.reports.report import (
    ReportDetail,
    ReportSection,
    ReportSectionSource,
    ReportSummary,
)


def get_database_connection_url() -> str:
    return settings.database_url.replace("+asyncpg", "")


def map_report_summary(row: asyncpg.Record) -> ReportSummary:
    return ReportSummary(
        id=row["id"],
        company_id=row["company_id"],
        status=row["status"],
        client_name=row["client_name"],
        address=row["address"],
        inspection_date=row["inspection_date"],
        inspector_name=row["inspector_name"],
    )


def map_report_detail(row: asyncpg.Record) -> ReportDetail:
    return ReportDetail(
        id=row["id"],
        status=row["status"],
        client_name=row["client_name"],
        address=row["address"],
        inspection_date=row["inspection_date"],
        inspector_name=row["inspector_name"],
        sections=[],
    )


def map_report_section_source(row: asyncpg.Record) -> ReportSectionSource:
    if row["source_type"] == "transcription_segment":
        return ReportSectionSource(
            type="audio",
            timestamp_start=row["timestamp_start"],
            timestamp_end=row["timestamp_end"],
            capture_time=None,
            content_summary=row["transcription_text"],
        )

    return ReportSectionSource(
        type="image",
        timestamp_start=None,
        timestamp_end=None,
        capture_time=row["capture_time"],
        content_summary=row["image_analysis_text"],
    )


async def list_report_summaries_by_company_id(company_id: str) -> list[ReportSummary]:
    connection = await asyncpg.connect(get_database_connection_url())

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


async def get_report_by_id(report_id: str, company_id: str) -> ReportDetail | None:
    connection = await asyncpg.connect(get_database_connection_url())

    try:
        row = await connection.fetchrow(
            """
            SELECT
                reports.id,
                reports.status,
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

    if row is None:
        return None

    return map_report_detail(row)


async def get_sections_with_sources(report_id: str) -> list[ReportSection]:
    connection = await asyncpg.connect(get_database_connection_url())

    try:
        rows = await connection.fetch(
            """
            SELECT
                report_sections.id,
                report_sections.section_key,
                report_sections.section_order,
                report_sections.ai_draft,
                report_sections.field_expert_content,
                report_sections.is_approved,
                report_section_sources.source_type,
                transcription_segments.start_seconds AS timestamp_start,
                transcription_segments.end_seconds AS timestamp_end,
                transcription_segments.text AS transcription_text,
                image_analyses.captured_at AS capture_time,
                image_analyses.analysis_text AS image_analysis_text
            FROM report_sections
            LEFT JOIN report_section_sources
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

    sections_by_id = {}
    sections = []

    for row in rows:
        section_id = row["id"]

        if section_id not in sections_by_id:
            section = ReportSection(
                id=section_id,
                section_key=row["section_key"],
                ai_draft=row["ai_draft"],
                field_expert_content=row["field_expert_content"],
                is_approved=row["is_approved"],
                sources=[],
            )
            sections_by_id[section_id] = section
            sections.append(section)

        if row["source_type"] is not None:
            sections_by_id[section_id].sources.append(map_report_section_source(row))

    return sections
