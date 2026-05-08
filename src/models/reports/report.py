from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ReportStatus = Literal["generating", "draft", "approved", "failed"]


class ReportSummary(BaseModel):
    id: UUID
    company_id: UUID
    status: ReportStatus
