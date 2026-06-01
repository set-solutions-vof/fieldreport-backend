from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from src.config import settings
from src.models.templates.pipeline import TemplateAnalysisFile


async def store_template_analysis_files(
    company_id: str,
    job_id: str,
    files: list[UploadFile],
) -> list[TemplateAnalysisFile]:
    job_directory = (
        Path(settings.template_analysis_stored_file_path).resolve() / company_id / job_id
    )
    job_directory.mkdir(parents=True, exist_ok=True)

    stored_files: list[TemplateAnalysisFile] = []

    for file in files:
        original_file_name = file.filename or f"{uuid4()}.pdf"
        file_extension = Path(original_file_name).suffix
        stored_original_file_name = f"{uuid4()}{file_extension}"
        stored_file_path = job_directory / stored_original_file_name
        file_content = await file.read()

        stored_file_path.write_bytes(file_content)
        await file.seek(0)

        stored_files.append(
            TemplateAnalysisFile(
                original_file_name=original_file_name,
                stored_file_path=str(stored_file_path),
            )
        )

    return stored_files


def load_template_analysis_file(stored_file_path: str) -> bytes:
    return Path(stored_file_path).read_bytes()
