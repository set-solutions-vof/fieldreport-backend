from pydantic import BaseModel, ConfigDict


class ReportSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    status: str

