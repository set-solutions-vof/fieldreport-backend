import asyncpg

from src.config import settings
from src.models.reports.report import (
    ReportDetail,
    ReportDetailSection,
    ReportSection,
    ReportSectionSource,
    ReportSummary,
    ReportTimelineItem,
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
        updated_at=row["updated_at"],
        sections=[],
    )


def map_report_section_source(row: asyncpg.Record) -> ReportSectionSource:
    if row["source_type"] == "transcription_segment":
        return ReportSectionSource(
            type="audio",
            timestamp_start=row["start_seconds"],
            timestamp_end=row["end_seconds"],
            capture_time=None,
            content_summary=row["transcription_text"],
        )

    return ReportSectionSource(
        type="image",
        timestamp_start=None,
        timestamp_end=None,
        capture_time=row["captured_at"],
        content_summary=row["image_analysis_text"],
    )


def map_report_timeline_item(row: asyncpg.Record) -> ReportTimelineItem:
    if row["source_type"] == "transcription_segment":
        return ReportTimelineItem(
            id=row["transcription_segment_id"],
            source_type="transcription_segment",
            timeline_offset_seconds=float(row["timeline_offset_seconds"]),
            start_seconds=row["start_seconds"],
            end_seconds=row["end_seconds"],
            captured_at=None,
            content_summary=row["transcription_text"],
        )

    return ReportTimelineItem(
        id=row["image_analysis_id"],
        source_type="image_analysis",
        timeline_offset_seconds=float(row["timeline_offset_seconds"]),
        start_seconds=None,
        end_seconds=None,
        captured_at=row["captured_at"],
        content_summary=row["image_analysis_text"],
    )


def map_report_sections(rows: list[asyncpg.Record]) -> list[ReportSection]:
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
                confidence_level=row["confidence_level"],
                confidence_score=float(row["confidence_score"]),
                sources=[],
            )
            sections_by_id[section_id] = section
            sections.append(section)

        if row["source_type"] is not None:
            sections_by_id[section_id].sources.append(map_report_section_source(row))

    return sections


def map_report_detail_sections(
    rows: list[asyncpg.Record],
) -> tuple[list[ReportDetailSection], list[ReportTimelineItem]]:
    sections_by_id = {}
    timeline_items_by_id = {}
    sections = []

    for row in rows:
        section_id = row["id"]

        if section_id not in sections_by_id:
            section = ReportDetailSection(
                id=section_id,
                section_key=row["section_key"],
                ai_draft=row["ai_draft"],
                field_expert_content=row["field_expert_content"],
                is_approved=row["is_approved"],
                confidence_level=row["confidence_level"],
                confidence_score=float(row["confidence_score"]),
                source_item_ids=[],
            )
            sections_by_id[section_id] = section
            sections.append(section)

        if row["source_type"] is None:
            continue

        timeline_item = map_report_timeline_item(row)
        sections_by_id[section_id].source_item_ids.append(timeline_item.id)
        timeline_items_by_id[timeline_item.id] = timeline_item

    timeline_items = sorted(
        timeline_items_by_id.values(),
        key=lambda timeline_item: (
            timeline_item.timeline_offset_seconds,
            timeline_item.source_type,
            str(timeline_item.id),
        ),
    )

    return sections, timeline_items


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


async def get_report_by_id(report_id: str, company_id: str) -> ReportDetail:
    connection = await asyncpg.connect(get_database_connection_url())

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
    connection = await asyncpg.connect(get_database_connection_url())

    try:
        return await connection.fetch(
            """
            SELECT
                report_sections.id,
                report_sections.section_key,
                report_sections.section_order,
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


async def get_report_detail_sections(
    report_id: str,
) -> tuple[list[ReportDetailSection], list[ReportTimelineItem]]:
    rows = await fetch_report_section_rows(report_id)

    return map_report_detail_sections(rows)


async def get_sections_with_sources(report_id: str) -> list[ReportSection]:
    rows = await fetch_report_section_rows(report_id)

    return map_report_sections(rows)


async def update_report_section(
    report_id: str,
    section_id: str,
    company_id: str,
    field_expert_content: str | None,
    is_approved: bool | None,
) -> ReportSection:
    connection = await asyncpg.connect(get_database_connection_url())

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
                report_sections.section_key,
                report_sections.section_order,
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
            LEFT JOIN report_section_sources
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
