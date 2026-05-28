from pydantic import BaseModel

from src.models.enums.report_status import ReportStatus


class CreateInspectionResponse(BaseModel):
    report_id: str
    status: ReportStatus
