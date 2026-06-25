from uuid import UUID

from pydantic import BaseModel

from src.models.enums.report_status import ReportStatus
from src.models.reports.metadata import ReportMetadata


class ReportPipelineContext(BaseModel):
    id: UUID
    inspection_id: UUID
    company_id: UUID
    template_id: UUID
    status: ReportStatus
    extra_context: str
    metadata: ReportMetadata


class InspectionMediaFile(BaseModel):
    storage_key: str
    original_file_name: str


class StoredTranscriptionSegment(BaseModel):
    id: UUID
    text: str
    start_seconds: float
    end_seconds: float


class StoredImageAnalysis(BaseModel):
    id: UUID
    analysis_text: str
    dji_metadata: dict | None = None
    thermal_metrics: dict | None = None
    panel_location_key: str | None = None
