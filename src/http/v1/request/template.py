from fastapi import UploadFile
from pydantic import BaseModel, Field


class StartTemplateAnalysisRequest(BaseModel):
    files: list[UploadFile] = Field(min_length=1)
