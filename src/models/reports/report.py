from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.templates.domain import TemplateSectionGroup, TemplateSectionRenderType

ReportStatus = Literal["generating", "draft", "approved", "failed"]
ReportSourceType = Literal["transcription_segment", "image_analysis"]


class ReportSummary(BaseModel):
    id: UUID
    company_id: UUID
    status: ReportStatus
    client_name: str
    address: str
    inspection_date: datetime
    inspector_name: str


class ReportSectionSource(BaseModel):
    type: Literal["audio", "image"]
    timestamp_start: float | None
    timestamp_end: float | None
    capture_time: datetime | None
    content_summary: str


class ReportTimelineItem(BaseModel):
    id: UUID
    source_type: ReportSourceType
    timeline_offset_seconds: float
    start_seconds: float | None
    end_seconds: float | None
    captured_at: datetime | None
    content_summary: str


class ReportSectionBase(BaseModel):
    id: UUID
    section_id: str
    label: str
    ai_draft: str
    field_expert_content: str | None
    is_approved: bool
    confidence_level: Literal["high", "medium", "low"]
    confidence_score: float
    render_type: TemplateSectionRenderType = "text_block"
    fields: list[str] | None = None
    groups: list[TemplateSectionGroup] | None = None


class ReportSection(ReportSectionBase):
    sources: list[ReportSectionSource]


class ReportDetailSection(ReportSectionBase):
    source_item_ids: list[UUID] = Field(default_factory=list)


class ReportDetail(BaseModel):
    id: UUID
    status: ReportStatus
    client_name: str
    address: str
    inspection_date: datetime
    inspector_name: str
    updated_at: datetime | None = None
    sections: list[ReportDetailSection]
    timeline_items: list[ReportTimelineItem] = Field(default_factory=list)
