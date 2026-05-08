from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.models.reports.report import (
    ReportDetail,
    ReportSection,
    ReportSectionSource,
    ReportSummary,
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
    sources: list[SectionSourceResponse]


class ReportDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    client_name: str
    address: str
    inspection_date: str
    inspector_name: str
    sections: list[ReportSectionResponse]


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
        sources=[section_source_response(source) for source in section.sources],
    )


def report_detail_response(report_detail: ReportDetail) -> ReportDetailResponse:
    return ReportDetailResponse(
        id=str(report_detail.id),
        status=report_detail.status,
        client_name=report_detail.client_name,
        address=report_detail.address,
        inspection_date=report_detail.inspection_date.isoformat(),
        inspector_name=report_detail.inspector_name,
        sections=[report_section_response(section) for section in report_detail.sections],
    )
