from uuid import uuid4

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
from src.models.reports.transcription import TranscriptionSegment


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


async def claim_next_audio_pipeline_report() -> dict | None:
    connection = await asyncpg.connect(get_connection_url())

    try:
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
    finally:
        await connection.close()

    return dict(row) if row is not None else None


async def get_report_for_pipeline(report_id: str) -> dict:
    connection = await asyncpg.connect(get_connection_url())

    try:
        row = await connection.fetchrow(
            """
            SELECT
                reports.id,
                reports.inspection_id,
                reports.company_id,
                reports.template_id,
                reports.status,
                inspections.extra_context,
                inspections.investigation_type,
                inspections.client_type
            FROM reports
            JOIN inspections ON inspections.id = reports.inspection_id
            WHERE reports.id = $1::uuid
            """,
            report_id,
        )
    finally:
        await connection.close()

    return dict(row)


async def set_report_status(report_id: str, status: str) -> None:
    connection = await asyncpg.connect(get_connection_url())

    try:
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
    finally:
        await connection.close()


async def insert_transcription(
    inspection_id: str,
    company_id: str,
    storage_key: str,
    raw_text: str,
    duration_seconds: float,
) -> str:
    connection = await asyncpg.connect(get_connection_url())
    transcription_id = str(uuid4())

    try:
        await connection.execute(
            """
            INSERT INTO transcriptions (
                id,
                inspection_id,
                company_id,
                storage_key,
                raw_text,
                created_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                $3::uuid,
                $4::text,
                $5::text,
                NOW()
            )
            """,
            transcription_id,
            inspection_id,
            company_id,
            storage_key,
            raw_text,
        )
    finally:
        await connection.close()

    return transcription_id


async def insert_transcription_segments(
    transcription_id: str,
    inspection_id: str,
    segments: list[TranscriptionSegment],
) -> list[str]:
    connection = await asyncpg.connect(get_connection_url())
    segment_ids = [str(uuid4()) for _ in segments]

    try:
        for segment_id, segment in zip(segment_ids, segments, strict=True):
            await connection.execute(
                """
                INSERT INTO transcription_segments (
                    id,
                    transcription_id,
                    inspection_id,
                    segment_index,
                    start_seconds,
                    end_seconds,
                    text,
                    created_at
                )
                VALUES (
                    $1::uuid,
                    $2::uuid,
                    $3::uuid,
                    $4::integer,
                    $5::double precision,
                    $6::double precision,
                    $7::text,
                    NOW()
                )
                """,
                segment_id,
                transcription_id,
                inspection_id,
                segment.segment_index,
                segment.start_seconds,
                segment.end_seconds,
                segment.text,
            )
    finally:
        await connection.close()

    return segment_ids


async def fetch_transcription_segments_for_inspection(
    inspection_id: str,
) -> list[asyncpg.Record]:
    connection = await asyncpg.connect(get_connection_url())

    try:
        return await connection.fetch(
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
    finally:
        await connection.close()


async def insert_image_analysis(
    inspection_id: str,
    company_id: str,
    storage_key: str,
    analysis_text: str,
) -> str:
    connection = await asyncpg.connect(get_connection_url())
    image_analysis_id = str(uuid4())

    try:
        await connection.execute(
            """
            INSERT INTO image_analyses (
                id,
                inspection_id,
                company_id,
                storage_key,
                analysis_text,
                geotag_lat,
                geotag_lng,
                captured_at,
                created_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                $3::uuid,
                $4::text,
                $5::text,
                NULL,
                NULL,
                NULL,
                NOW()
            )
            """,
            image_analysis_id,
            inspection_id,
            company_id,
            storage_key,
            analysis_text,
        )
    finally:
        await connection.close()

    return image_analysis_id


async def fetch_image_analyses_for_inspection(inspection_id: str) -> list[asyncpg.Record]:
    connection = await asyncpg.connect(get_connection_url())

    try:
        return await connection.fetch(
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
    finally:
        await connection.close()


async def insert_report_section(
    report_id: str,
    company_id: str,
    section_id: str,
    section_order: int,
    render_type: str,
    ai_draft_text: str,
    confidence_level: str,
    confidence_score: float,
) -> str:
    connection = await asyncpg.connect(get_connection_url())
    report_section_id = str(uuid4())

    try:
        await connection.execute(
            """
            INSERT INTO report_sections (
                id,
                report_id,
                company_id,
                section_id,
                section_order,
                render_type,
                ai_content,
                expert_content,
                edit_distance,
                is_approved,
                confidence_level,
                confidence_score,
                updated_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                $3::uuid,
                $4::text,
                $5::integer,
                $6::render_type_enum,
                to_jsonb(ARRAY[$7::text]),
                NULL,
                NULL,
                false,
                $8::confidence_level_enum,
                $9::numeric,
                NOW()
            )
            """,
            report_section_id,
            report_id,
            company_id,
            section_id,
            section_order,
            render_type,
            ai_draft_text,
            confidence_level,
            confidence_score,
        )
    finally:
        await connection.close()

    return report_section_id


async def insert_report_section_source_transcription(
    report_section_id: str,
    transcription_segment_id: str,
) -> None:
    connection = await asyncpg.connect(get_connection_url())

    try:
        await connection.execute(
            """
            INSERT INTO report_section_sources (
                id,
                report_section_id,
                source_type,
                transcription_segment_id,
                image_analysis_id,
                created_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                'transcription_segment'::report_section_source_type,
                $3::uuid,
                NULL,
                NOW()
            )
            """,
            str(uuid4()),
            report_section_id,
            transcription_segment_id,
        )
    finally:
        await connection.close()


async def insert_report_section_source_image(
    report_section_id: str,
    image_analysis_id: str,
) -> None:
    connection = await asyncpg.connect(get_connection_url())

    try:
        await connection.execute(
            """
            INSERT INTO report_section_sources (
                id,
                report_section_id,
                source_type,
                transcription_segment_id,
                image_analysis_id,
                created_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                'image_analysis'::report_section_source_type,
                NULL,
                $3::uuid,
                NOW()
            )
            """,
            str(uuid4()),
            report_section_id,
            image_analysis_id,
        )
    finally:
        await connection.close()
