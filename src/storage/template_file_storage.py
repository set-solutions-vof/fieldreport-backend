from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from src.config import settings
from src.models.templates.pipeline import TemplateAnalysisFile


def get_template_analysis_storage_directory() -> Path:
    return Path(settings.template_analysis_storage_path).resolve()


async def store_template_analysis_files(
    company_id: str,
    job_id: str,
    files: list[UploadFile],
) -> list[TemplateAnalysisFile]:
    job_directory = get_template_analysis_storage_directory() / company_id / job_id
    job_directory.mkdir(parents=True, exist_ok=True)

    stored_files: list[TemplateAnalysisFile] = []

    for file in files:
        file_name = file.filename or f"{uuid4()}.pdf"
        file_extension = Path(file_name).suffix
        stored_file_name = f"{uuid4()}{file_extension}"
        storage_path = job_directory / stored_file_name
        file_content = await file.read()

        storage_path.write_bytes(file_content)
        await file.seek(0)

        stored_files.append(
            TemplateAnalysisFile(file_name=file_name, storage_path=str(storage_path))
        )

    return stored_files


def load_template_analysis_file(storage_path: str) -> bytes:
    return Path(storage_path).read_bytes()
