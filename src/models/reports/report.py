from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.templates.domain import TemplateSectionGroup, TemplateSectionRenderType

ReportStatus = Literal["generating", "draft", "approved", "failed"]
ReportEvidenceItemType = Literal["transcription_segment", "image_analysis"]


class ReportSummary(BaseModel):
    id: UUID
    company_id: UUID
    status: ReportStatus
    client_name: str
    address: str
    inspection_date: datetime
    inspector_name: str


class ReportEvidenceSource(BaseModel):
    type: Literal["audio", "image"]
    start_seconds: float | None
    end_seconds: float | None
    captured_at: datetime | None
    content_summary: str


class ReportEvidenceItem(BaseModel):
    id: UUID
    evidence_type: ReportEvidenceItemType
    timeline_seconds: float
    start_seconds: float | None
    end_seconds: float | None
    captured_at: datetime | None
    content_summary: str


class ReportSectionContent(BaseModel):
    id: UUID
    section_id: str
    label: str
    generated_content: str
    reviewed_content: str | None
    approved: bool
    confidence_level: Literal["high", "medium", "low"]
    confidence_score: float
    render_type: TemplateSectionRenderType = "text_block"
    fields: list[str] | None = None
    groups: list[TemplateSectionGroup] | None = None


class ReportSection(ReportSectionContent):
    evidence_sources: list[ReportEvidenceSource]


class ReportDetailSection(ReportSectionContent):
    evidence_item_ids: list[UUID] = Field(default_factory=list)


class ReportDetail(BaseModel):
    id: UUID
    status: ReportStatus
    client_name: str
    address: str
    inspection_date: datetime
    inspector_name: str
    updated_at: datetime | None = None
    sections: list[ReportDetailSection]
    evidence_items: list[ReportEvidenceItem] = Field(default_factory=list)
