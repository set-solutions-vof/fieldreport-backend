import asyncio

from src.db import template_queries
from src.llm import deepseek_client, gpt4o_client
from src.models.templates.pipeline import TemplateAnalysisDocument
from src.models.templates.records import TemplateAnalysisJobRecord
from src.storage import template_file_storage
from src.utils import pdf_text_extractor


async def process_next_template_analysis_job() -> TemplateAnalysisJobRecord | None:
    job = await template_queries.claim_next_template_analysis_job()

    if job is None:
        return None

    try:
        job_id = str(job.id)
        files = await template_queries.get_template_analysis_job_files(job_id)
        documents = await asyncio.gather(
            *[
                build_template_analysis_document(
                    file.original_file_name,
                    file.stored_file_path,
                )
                for file in files
            ]
        )
        structure = await deepseek_client.synthesize_template_structure(documents)

        await template_queries.update_template_analysis_job(
            job_id,
            "pending_review",
            structure,
        )
    except Exception as error:
        await template_queries.update_template_analysis_job(
            job_id,
            "failed",
            None,
            failure_message=str(error),
        )
        raise

    return job


async def build_template_analysis_document(
    original_file_name: str,
    stored_file_path: str,
) -> TemplateAnalysisDocument:
    file_content = template_file_storage.load_template_analysis_file(stored_file_path)
    extracted_text, visual_summary = await asyncio.gather(
        asyncio.to_thread(pdf_text_extractor.extract_text_from_pdf, stored_file_path),
        gpt4o_client.analyze_pdf_visuals(original_file_name, file_content),
    )

    return TemplateAnalysisDocument(
        original_file_name=original_file_name,
        extracted_text=extracted_text,
        visual_summary=visual_summary,
    )
