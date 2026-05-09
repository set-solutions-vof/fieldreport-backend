from pydantic import BaseModel


class ReportSectionUpdateRequest(BaseModel):
    field_expert_content: str | None = None
    is_approved: bool | None = None
