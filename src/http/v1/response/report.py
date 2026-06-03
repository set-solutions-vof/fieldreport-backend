from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.models.enums.confidence_level import ConfidenceLevel
from src.models.enums.evidence_source_type import EvidenceSourceType
from src.models.enums.report_evidence_item_type import ReportEvidenceItemType
from src.models.enums.template_section_render_type import TemplateSectionRenderType
from src.models.reports.metadata import ReportMetadata
from src.models.reports.report import ReportDetail, ReportSection, ReportSummary
from src.models.templates.domain import TemplateSectionGroup


class ReportSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    status: str
    metadata: ReportMetadata
    inspection_date: datetime
    inspector_name: str


class EvidenceSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: EvidenceSourceType
    start_seconds: float | None
    end_seconds: float | None
    captured_at: datetime | None
    content_summary: str


class ReportSectionContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    section_id: str
    label: str
    generated_content: str
    reviewed_content: str | None
    approved: bool
    confidence_level: ConfidenceLevel
    confidence_score: float
    render_type: TemplateSectionRenderType = "text_block"
    fields: list[str] | None = None
    groups: list[TemplateSectionGroup] | None = None


class ReportSectionResponse(ReportSectionContentResponse):
    evidence_sources: list[EvidenceSourceResponse]


class EvidenceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    evidence_type: ReportEvidenceItemType
    timeline_seconds: float
    start_seconds: float | None
    end_seconds: float | None
    captured_at: datetime | None
    content_summary: str


class ReportDetailSectionResponse(ReportSectionContentResponse):
    evidence_item_ids: list[UUID]


class ReportDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    metadata: ReportMetadata
    inspection_date: datetime
    inspector_name: str
    updated_at: datetime | None = None
    sections: list[ReportDetailSectionResponse]
    evidence_items: list[EvidenceItemResponse]


def report_summary_response(report_summary: ReportSummary) -> ReportSummaryResponse:
    return ReportSummaryResponse.model_validate(report_summary)


def report_summary_responses(report_summaries: list[ReportSummary]) -> list[ReportSummaryResponse]:
    return [report_summary_response(report_summary) for report_summary in report_summaries]


def report_section_response(section: ReportSection) -> ReportSectionResponse:
    return ReportSectionResponse.model_validate(section.model_dump(mode="json"))


def report_detail_response(report_detail: ReportDetail) -> ReportDetailResponse:
    return ReportDetailResponse.model_validate(report_detail.model_dump(mode="json"))
