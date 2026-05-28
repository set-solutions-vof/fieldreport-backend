from fastapi import UploadFile
from pydantic import BaseModel, Field

from src.models.templates.domain import TemplateSection


class StartTemplateAnalysisRequest(BaseModel):
    files: list[UploadFile] = Field(min_length=1)


class TemplateStructureRequest(BaseModel):
    sections: list[TemplateSection]
