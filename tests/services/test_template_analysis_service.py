from unittest.mock import AsyncMock, patch

from src.models.templates.configuration import StoredTemplateStructure, TemplateSection
from src.models.templates.pipeline import (
    TemplateAnalysisDocument,
    TemplateAnalysisFile,
    TemplateAnalysisJob,
)
from src.services import template_analysis as template_analysis_service


async def test_build_template_analysis_document_combines_text_and_visual_outputs() -> None:
    with (
        patch.object(
            template_analysis_service.template_file_storage,
            "load_template_analysis_file",
            return_value=b"pdf-bytes",
        ),
        patch.object(
            template_analysis_service.pdf_extractor,
            "extract_text_from_pdf",
            return_value="Extracted text",
        ),
        patch.object(
            template_analysis_service.gpt4o_client,
            "analyze_pdf_visuals",
            AsyncMock(return_value='{"visual_summary":"Visual summary"}'),
        ),
    ):
        result = await template_analysis_service.build_template_analysis_document(
            "report.pdf",
            "/tmp/report.pdf",
        )

    assert result == TemplateAnalysisDocument(
        file_name="report.pdf",
        extracted_text="Extracted text",
        visual_summary='{"visual_summary":"Visual summary"}',
    )


async def test_process_next_template_analysis_job_returns_none_when_queue_is_empty() -> None:
    with patch.object(
        template_analysis_service.template_repository,
        "claim_next_template_analysis_job",
        AsyncMock(return_value=None),
    ):
        result = await template_analysis_service.process_next_template_analysis_job()

    assert result is None


async def test_process_next_template_analysis_job_updates_pending_review_structure() -> None:
    job = TemplateAnalysisJob(
        id="job-1",
        company_id="company-1",
        status="processing",
        reports_count=1,
    )
    files = [TemplateAnalysisFile(file_name="report.pdf", storage_path="/tmp/report.pdf")]
    sections = [TemplateSection(id="summary", label="Summary", type="text_block")]

    with (
        patch.object(
            template_analysis_service.template_repository,
            "claim_next_template_analysis_job",
            AsyncMock(return_value=job),
        ),
        patch.object(
            template_analysis_service.template_repository,
            "get_template_analysis_job_files",
            AsyncMock(return_value=files),
        ),
        patch.object(
            template_analysis_service,
            "build_template_analysis_document",
            AsyncMock(
                return_value=TemplateAnalysisDocument(
                    file_name="report.pdf",
                    extracted_text="Extracted text",
                    visual_summary="Visual summary",
                )
            ),
        ),
        patch.object(
            template_analysis_service.deepseek_client,
            "synthesize_template_sections",
            AsyncMock(return_value=sections),
        ),
        patch.object(
            template_analysis_service.template_repository,
            "update_template_analysis_job",
            AsyncMock(),
        ) as update_job,
    ):
        result = await template_analysis_service.process_next_template_analysis_job()

    assert result == job
    update_job.assert_awaited_once_with(
        "job-1",
        "pending_review",
        StoredTemplateStructure(sections=sections),
    )


async def test_process_next_template_analysis_job_marks_failed_when_model_call_fails() -> None:
    job = TemplateAnalysisJob(
        id="job-1",
        company_id="company-1",
        status="processing",
        reports_count=1,
    )
    files = [TemplateAnalysisFile(file_name="report.pdf", storage_path="/tmp/report.pdf")]

    with (
        patch.object(
            template_analysis_service.template_repository,
            "claim_next_template_analysis_job",
            AsyncMock(return_value=job),
        ),
        patch.object(
            template_analysis_service.template_repository,
            "get_template_analysis_job_files",
            AsyncMock(return_value=files),
        ),
        patch.object(
            template_analysis_service,
            "build_template_analysis_document",
            AsyncMock(
                return_value=TemplateAnalysisDocument(
                    file_name="report.pdf",
                    extracted_text="Extracted text",
                    visual_summary="Visual summary",
                )
            ),
        ),
        patch.object(
            template_analysis_service.deepseek_client,
            "synthesize_template_sections",
            AsyncMock(side_effect=ValueError("bad json")),
        ),
        patch.object(
            template_analysis_service.template_repository,
            "update_template_analysis_job",
            AsyncMock(),
        ) as update_job,
    ):
        try:
            await template_analysis_service.process_next_template_analysis_job()
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")

    update_job.assert_awaited_once_with(
        "job-1",
        "failed",
        None,
        error_message="bad json",
    )
