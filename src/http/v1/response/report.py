from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.models.reports.report import (
    ReportDetail,
    ReportDetailSection,
    ReportSection,
    ReportSectionSource,
    ReportSummary,
    ReportTimelineItem,
)


class ReportSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    status: str
    client_name: str
    address: str
    inspection_date: str
    inspector_name: str


class SectionSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: Literal["audio", "image"]
    timestamp_start: float | None
    timestamp_end: float | None
    capture_time: str | None
    content_summary: str


class ReportSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    section_key: str
    label: str
    ai_draft: str
    field_expert_content: str | None
    is_approved: bool
    confidence_level: str
    confidence_score: float
    sources: list[SectionSourceResponse]


class TimelineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_type: Literal["transcription_segment", "image_analysis"]
    timeline_offset_seconds: float
    start_seconds: float | None
    end_seconds: float | None
    captured_at: str | None
    content_summary: str


class ReportDetailSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    section_key: str
    label: str
    ai_draft: str
    field_expert_content: str | None
    is_approved: bool
    confidence_level: str
    confidence_score: float
    source_item_ids: list[str]


class ReportDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    client_name: str
    address: str
    inspection_date: str
    inspector_name: str
    updated_at: str | None = None
    sections: list[ReportDetailSectionResponse]
    timeline_items: list[TimelineItemResponse]


def report_summary_response(report_summary: ReportSummary) -> ReportSummaryResponse:
    return ReportSummaryResponse(
        id=str(report_summary.id),
        company_id=str(report_summary.company_id),
        status=report_summary.status,
        client_name=report_summary.client_name,
        address=report_summary.address,
        inspection_date=report_summary.inspection_date.isoformat(),
        inspector_name=report_summary.inspector_name,
    )


def report_summary_responses(report_summaries: list[ReportSummary]) -> list[ReportSummaryResponse]:
    return [report_summary_response(report_summary) for report_summary in report_summaries]


def section_source_response(source: ReportSectionSource) -> SectionSourceResponse:
    capture_time = source.capture_time.isoformat() if source.capture_time is not None else None

    return SectionSourceResponse(
        type=source.type,
        timestamp_start=source.timestamp_start,
        timestamp_end=source.timestamp_end,
        capture_time=capture_time,
        content_summary=source.content_summary,
    )


def report_section_response(section: ReportSection) -> ReportSectionResponse:
    return ReportSectionResponse(
        id=str(section.id),
        section_key=section.section_key,
        label=section.section_key.replace("_", " ").title(),
        ai_draft=section.ai_draft,
        field_expert_content=section.field_expert_content,
        is_approved=section.is_approved,
        confidence_level=section.confidence_level,
        confidence_score=section.confidence_score,
        sources=[section_source_response(source) for source in section.sources],
    )


def timeline_item_response(timeline_item: ReportTimelineItem) -> TimelineItemResponse:
    captured_at = (
        timeline_item.captured_at.isoformat() if timeline_item.captured_at is not None else None
    )

    return TimelineItemResponse(
        id=str(timeline_item.id),
        source_type=timeline_item.source_type,
        timeline_offset_seconds=timeline_item.timeline_offset_seconds,
        start_seconds=timeline_item.start_seconds,
        end_seconds=timeline_item.end_seconds,
        captured_at=captured_at,
        content_summary=timeline_item.content_summary,
    )


def report_detail_section_response(section: ReportDetailSection) -> ReportDetailSectionResponse:
    return ReportDetailSectionResponse(
        id=str(section.id),
        section_key=section.section_key,
        label=section.section_key.replace("_", " ").title(),
        ai_draft=section.ai_draft,
        field_expert_content=section.field_expert_content,
        is_approved=section.is_approved,
        confidence_level=section.confidence_level,
        confidence_score=section.confidence_score,
        source_item_ids=[str(source_item_id) for source_item_id in section.source_item_ids],
    )


def report_detail_response(report_detail: ReportDetail) -> ReportDetailResponse:
    return ReportDetailResponse(
        id=str(report_detail.id),
        status=report_detail.status,
        client_name=report_detail.client_name,
        address=report_detail.address,
        inspection_date=report_detail.inspection_date.isoformat(),
        inspector_name=report_detail.inspector_name,
        updated_at=report_detail.updated_at.isoformat()
        if report_detail.updated_at is not None
        else None,
        sections=[report_detail_section_response(section) for section in report_detail.sections],
        timeline_items=[
            timeline_item_response(timeline_item) for timeline_item in report_detail.timeline_items
        ],
    )
