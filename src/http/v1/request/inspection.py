from fastapi import UploadFile
from pydantic import BaseModel, Field


class CreateInspectionRequest(BaseModel):
    address: str
    inspection_date: str
    investigation_type: str
    client_type: str
    reference_number: str | None = None
    extra_context: str | None = None
    audio_files: list[UploadFile]
    photo_files: list[UploadFile] = Field(default_factory=list)
