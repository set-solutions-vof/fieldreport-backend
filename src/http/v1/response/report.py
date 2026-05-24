from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.models.reports.report import (
    ReportDetail,
    ReportSection,
    ReportSummary,
)


class ReportSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    status: str
    client_name: str
    address: str
    inspection_date: datetime
    inspector_name: str


class SectionSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: Literal["audio", "image"]
    timestamp_start: float | None
    timestamp_end: float | None
    capture_time: datetime | None
    content_summary: str


class ReportSectionResponseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    section_id: str
    label: str
    ai_draft: str
    field_expert_content: str | None
    is_approved: bool
    confidence_level: str
    confidence_score: float
    render_type: str = "text_block"
    fields: list[str] | None = None
    groups: list[dict] | None = None


class ReportSectionResponse(ReportSectionResponseBase):
    sources: list[SectionSourceResponse]


class TimelineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_type: Literal["transcription_segment", "image_analysis"]
    timeline_offset_seconds: float
    start_seconds: float | None
    end_seconds: float | None
    captured_at: datetime | None
    content_summary: str


class ReportDetailSectionResponse(ReportSectionResponseBase):
    source_item_ids: list[UUID]


class ReportDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    client_name: str
    address: str
    inspection_date: datetime
    inspector_name: str
    updated_at: datetime | None = None
    sections: list[ReportDetailSectionResponse]
    timeline_items: list[TimelineItemResponse]


def report_summary_response(report_summary: ReportSummary) -> ReportSummaryResponse:
    return ReportSummaryResponse.model_validate(report_summary)


def report_summary_responses(report_summaries: list[ReportSummary]) -> list[ReportSummaryResponse]:
    return [report_summary_response(report_summary) for report_summary in report_summaries]


def report_section_response(section: ReportSection) -> ReportSectionResponse:
    return ReportSectionResponse.model_validate(section.model_dump(mode="json"))


def report_detail_response(report_detail: ReportDetail) -> ReportDetailResponse:
    return ReportDetailResponse.model_validate(report_detail.model_dump(mode="json"))
