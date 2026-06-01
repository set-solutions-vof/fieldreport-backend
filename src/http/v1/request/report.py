from pydantic import BaseModel


class ReportSectionUpdateRequest(BaseModel):
    reviewed_content: str | None = None
    approved: bool | None = None
