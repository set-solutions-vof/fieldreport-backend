import asyncpg

from src.models.reports.report import (
    ReportDetail,
    ReportDetailSection,
    ReportEvidenceItem,
    ReportEvidenceSource,
    ReportSection,
    ReportSummary,
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


def map_report_section_source(row: asyncpg.Record) -> ReportEvidenceSource:
    if row["evidence_type"] == "transcription_segment":
        return ReportEvidenceSource(
            type="audio",
            start_seconds=row["start_seconds"],
            end_seconds=row["end_seconds"],
            captured_at=None,
            content_summary=row["transcription_text"],
        )

    return ReportEvidenceSource(
        type="image",
        start_seconds=None,
        end_seconds=None,
        captured_at=row["captured_at"],
        content_summary=row["image_analysis_text"],
    )


def map_report_evidence_item(row: asyncpg.Record) -> ReportEvidenceItem:
    if row["evidence_type"] == "transcription_segment":
        return ReportEvidenceItem(
            id=row["transcription_segment_id"],
            evidence_type="transcription_segment",
            timeline_seconds=float(row["timeline_seconds"]),
            start_seconds=row["start_seconds"],
            end_seconds=row["end_seconds"],
            captured_at=None,
            content_summary=row["transcription_text"],
        )

    return ReportEvidenceItem(
        id=row["image_analysis_id"],
        evidence_type="image_analysis",
        timeline_seconds=float(row["timeline_seconds"]),
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
                section_id=row["section_id"],
                label=row["section_id"].replace("_", " ").title(),
                generated_content=row["generated_content"],
                reviewed_content=row["reviewed_content"],
                approved=row["approved"],
                confidence_level=row["confidence_level"],
                confidence_score=float(row["confidence_score"]),
                render_type=row["render_type"],
                evidence_sources=[],
            )
            sections_by_id[section_id] = section
            sections.append(section)

        sections_by_id[section_id].evidence_sources.append(map_report_section_source(row))

    return sections


def map_report_detail_sections(
    rows: list[asyncpg.Record],
) -> tuple[list[ReportDetailSection], list[ReportEvidenceItem]]:
    sections_by_id: dict[object, ReportDetailSection] = {}
    evidence_items_by_id: dict[object, ReportEvidenceItem] = {}
    sections: list[ReportDetailSection] = []

    for row in rows:
        section_id = row["id"]

        if section_id not in sections_by_id:
            section = ReportDetailSection(
                id=section_id,
                section_id=row["section_id"],
                label=row["section_id"].replace("_", " ").title(),
                generated_content=row["generated_content"],
                reviewed_content=row["reviewed_content"],
                approved=row["approved"],
                confidence_level=row["confidence_level"],
                confidence_score=float(row["confidence_score"]),
                render_type=row["render_type"],
                evidence_item_ids=[],
            )
            sections_by_id[section_id] = section
            sections.append(section)

        evidence_item = map_report_evidence_item(row)
        sections_by_id[section_id].evidence_item_ids.append(evidence_item.id)
        evidence_items_by_id[evidence_item.id] = evidence_item

    evidence_items = sorted(
        evidence_items_by_id.values(),
        key=lambda item: (
            item.timeline_seconds,
            item.evidence_type,
            str(item.id),
        ),
    )

    return sections, evidence_items
