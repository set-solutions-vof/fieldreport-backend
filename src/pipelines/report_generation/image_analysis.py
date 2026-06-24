from pathlib import Path

from loguru import logger

from src.db.inspection.queries import fetch_inspection_photo_files
from src.db.report.pipeline_repository import ReportPipelineRepository
from src.llm import gpt4o_client
from src.models.reports.pipeline import ReportPipelineContext
from src.prompts.image_analysis import IMAGE_ANALYSIS_PROMPT, THERMAL_IMAGE_ANALYSIS_PROMPT
from src.storage import blob
from src.utils.dji_xmp import extract_dji_xmp


async def analyze_inspection_photo_files(
    report: ReportPipelineContext,
    repository: ReportPipelineRepository,
) -> None:
    photo_files = await fetch_inspection_photo_files(str(report.inspection_id))

    for photo_file in photo_files:
        photo_key = photo_file.storage_key
        try:
            file_content = (await blob.download_file("inspections", photo_key))[0]
            dji_meta = extract_dji_xmp(file_content)
            prompt = (
                THERMAL_IMAGE_ANALYSIS_PROMPT
                if dji_meta and dji_meta.image_source == "InfraredCamera"
                else IMAGE_ANALYSIS_PROMPT
            )
            description = await gpt4o_client.analyze_inspection_photo(
                Path(photo_key).name,
                file_content,
                prompt=prompt,
            )
            image_analysis_id = await repository.insert_image_analysis(
                str(report.inspection_id),
                str(report.company_id),
                photo_key,
                description,
                dji_metadata=dji_meta.model_dump(mode="json") if dji_meta else None,
            )
            logger.info("Analyzed photo {} as image_analysis {}", photo_key, image_analysis_id)
        except Exception:
            logger.exception("Photo file {} failed", photo_key)
            raise
