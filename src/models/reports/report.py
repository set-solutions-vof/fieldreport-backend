from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ReportStatus = Literal["generating", "draft", "approved", "failed"]
ReportSectionSourceType = Literal["audio", "image"]


class ReportSummary(BaseModel):
    id: UUID
    company_id: UUID
    status: ReportStatus
    client_name: str
    address: str
    inspection_date: datetime
    inspector_name: str


class ReportSectionSource(BaseModel):
    type: ReportSectionSourceType
    timestamp_start: float | None
    timestamp_end: float | None
    capture_time: datetime | None
    content_summary: str


class ReportSection(BaseModel):
    id: UUID
    section_key: str
    ai_draft: str
    field_expert_content: str | None
    is_approved: bool
    sources: list[ReportSectionSource]


class ReportDetail(BaseModel):
    id: UUID
    status: ReportStatus
    client_name: str
    address: str
    inspection_date: datetime
    inspector_name: str
    sections: list[ReportSection]
