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
    section_key: str
    label: str
    ai_draft: str
    field_expert_content: str | None
    is_approved: bool
    confidence_level: str
    confidence_score: float


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
    section_data = section.model_dump()
    section_data["label"] = section.section_key.replace("_", " ").title()

    return ReportSectionResponse.model_validate(section_data)


def report_detail_response(report_detail: ReportDetail) -> ReportDetailResponse:
    report_data = report_detail.model_dump()
    report_data["sections"] = []

    for section in report_detail.sections:
        section_data = section.model_dump()
        section_data["label"] = section.section_key.replace("_", " ").title()
        report_data["sections"].append(section_data)

    return ReportDetailResponse.model_validate(report_data)
