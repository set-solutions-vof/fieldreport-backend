from fastapi import UploadFile
from pydantic import BaseModel, Field


class CreateInspectionRequest(BaseModel):
    metadata: str
    extra_context: str | None = None
    audio_files: list[UploadFile] = Field(min_length=1)
    photo_files: list[UploadFile] = Field(default_factory=list)
