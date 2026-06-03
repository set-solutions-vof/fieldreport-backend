from pydantic import BaseModel, ConfigDict


class ReportMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")
