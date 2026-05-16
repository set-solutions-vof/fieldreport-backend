import asyncio

from loguru import logger

from src.db import template_queries
from src.llm import deepseek_client, gpt4o_client
from src.models.templates.configuration import StoredTemplateStructure
from src.models.templates.pipeline import TemplateAnalysisDocument, TemplateAnalysisJob
from src.pdf import extractor as pdf_extractor
from src.storage import template_file_storage


async def process_next_template_analysis_job() -> TemplateAnalysisJob | None:
    job = await template_queries.claim_next_template_analysis_job()

    if job is None:
        return None

    logger.info("Processing template analysis job {}", job.id)

    try:
        files = await template_queries.get_template_analysis_job_files(job.id)
        logger.debug("Job {} has {} file(s)", job.id, len(files))

        documents = await asyncio.gather(
            *[build_template_analysis_document(file.file_name, file.storage_path) for file in files]
        )
        sections = await deepseek_client.synthesize_template_sections(documents)
        logger.debug("DeepSeek synthesized {} section(s) for job {}", len(sections), job.id)

        structure = StoredTemplateStructure(sections=sections)

        await template_queries.update_template_analysis_job(
            job.id,
            "pending_review",
            structure,
        )
        logger.info("Job {} completed, status=pending_review", job.id)
    except Exception as error:
        logger.error("Job {} failed: {}", job.id, error)
        await template_queries.update_template_analysis_job(
            job.id,
            "failed",
            None,
            error_message=str(error),
        )
        raise

    return job


async def build_template_analysis_document(
    file_name: str,
    storage_path: str,
) -> TemplateAnalysisDocument:
    logger.debug("Building analysis document for {}", file_name)
    file_content = template_file_storage.load_template_analysis_file(storage_path)
    extracted_text, visual_summary = await asyncio.gather(
        asyncio.to_thread(pdf_extractor.extract_text_from_pdf, storage_path),
        gpt4o_client.analyze_pdf_visuals(file_name, file_content),
    )
    logger.debug(
        "Extracted {} chars of text and visual summary for {}", len(extracted_text), file_name
    )

    return TemplateAnalysisDocument(
        file_name=file_name,
        extracted_text=extracted_text,
        visual_summary=visual_summary,
    )
