from typing import Literal

from pydantic import BaseModel


class CreateInspectionResponse(BaseModel):
    report_id: str
    status: Literal["processing"]
