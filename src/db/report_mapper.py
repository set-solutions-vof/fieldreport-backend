import asyncpg

from src.models.reports.report import (
    ReportDetail,
    ReportDetailSection,
    ReportSection,
    ReportSectionSource,
    ReportSummary,
    ReportTimelineItem,
)


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
    sections_by_id: dict[object, ReportSection] = {}
    sections: list[ReportSection] = []

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
    sections_by_id: dict[object, ReportDetailSection] = {}
    timeline_items_by_id: dict[object, ReportTimelineItem] = {}
    sections: list[ReportDetailSection] = []

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
        key=lambda item: (
            item.timeline_offset_seconds,
            item.source_type,
            str(item.id),
        ),
    )

    return sections, timeline_items
