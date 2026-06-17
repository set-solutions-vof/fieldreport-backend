from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.enums.confidence_level import ConfidenceLevel
from src.models.enums.evidence_source_type import EvidenceSourceType
from src.models.enums.report_status import ReportStatus
from src.models.enums.template_section_render_type import TemplateSectionRenderType
from src.models.reports.metadata import ReportMetadata
from src.models.templates.domain import TemplateSectionGroup


class ReportSummary(BaseModel):
    id: UUID
    company_id: UUID
    status: ReportStatus
    metadata: ReportMetadata
    inspection_date: datetime
    inspector_name: str


class ReportEvidenceSource(BaseModel):
    type: EvidenceSourceType
    start_seconds: float | None
    end_seconds: float | None
    captured_at: datetime | None
    content_summary: str


class TranscriptionEvidenceItem(BaseModel):
    id: UUID
    evidence_type: Literal["transcription_segment"] = "transcription_segment"
    timeline_seconds: float
    start_seconds: float
    end_seconds: float
    content_summary: str
    transcription_id: UUID


class ImageEvidenceItem(BaseModel):
    id: UUID
    evidence_type: Literal["image_analysis"] = "image_analysis"
    timeline_seconds: float | None = None
    captured_at: datetime | None
    content_summary: str
    storage_key: str | None = None


class ReportSectionContent(BaseModel):
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


class ReportSection(ReportSectionContent):
    evidence_sources: list[ReportEvidenceSource]


class ReportDetailSection(ReportSectionContent):
    evidence_item_ids: list[UUID] = Field(default_factory=list)


class ReportDetail(BaseModel):
    id: UUID
    status: ReportStatus
    metadata: ReportMetadata
    inspection_date: datetime
    inspector_name: str
    updated_at: datetime | None = None
    sections: list[ReportDetailSection]
    evidence_items: list[TranscriptionEvidenceItem | ImageEvidenceItem] = Field(
        default_factory=list
    )
