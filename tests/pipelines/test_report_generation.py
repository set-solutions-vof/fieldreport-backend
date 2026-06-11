from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.models.reports.generation import GeneratedReportSection
from src.models.reports.metadata import ReportMetadata
from src.models.reports.pipeline import StoredImageAnalysis, StoredTranscriptionSegment
from src.models.templates.domain import (
    TemplateScalarMetadataField,
    TemplateSection,
    TemplateStructure,
)
from src.pipelines.report_generation import generation
from tests.pipelines.helpers import build_report


def test_build_report_generation_prompt_includes_metadata_and_extra_context() -> None:
    report = build_report()
    template_structure = TemplateStructure(
        metadata_fields=[
            TemplateScalarMetadataField(key="type_klant", label="Type klant", type="text")
        ],
        sections=[TemplateSection(id="conclusie", label="Conclusie", render_type="text_block")],
    )

    prompt = generation.build_report_generation_prompt(
        template_structure,
        template_structure.sections,
        [StoredTranscriptionSegment(id=uuid4(), text="Transcript")],
        [StoredImageAnalysis(id=uuid4(), analysis_text="Image")],
        report,
    )

    assert "Type klant: Zakelijk" in prompt
    assert "Extra opmerkingen: Extra" in prompt
    assert "Transcript" in prompt
    assert "Image" in prompt


def test_build_report_generation_prompt_omits_context_when_empty() -> None:
    report = build_report()
    report = report.model_copy(update={"extra_context": "", "metadata": ReportMetadata()})
    template_structure = TemplateStructure(
        sections=[TemplateSection(id="conclusie", label="Conclusie", render_type="text_block")]
    )

    prompt = generation.build_report_generation_prompt(
        template_structure,
        template_structure.sections,
        [],
        [],
        report,
    )

    assert "Extra context:" not in prompt


async def test_generate_report_sections_parses_llm_response() -> None:
    report = build_report()
    template_structure = TemplateStructure(
        sections=[TemplateSection(id="conclusie", label="Conclusie", render_type="text_block")]
    )
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=(
                        '{"sections":[{"id":"conclusie","generated_content":"Concept",'
                        '"confidence_level":"high","confidence_score":0.9}]}'
                    )
                )
            )
        ]
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=response)))
    )

    with patch.object(generation.client_factory, "get_gpt4o_client", return_value=client):
        sections = await generation.generate_report_sections(
            report,
            template_structure,
            template_structure.sections,
            [],
            [],
        )

    assert sections[0].id == "conclusie"
    assert sections[0].generated_content == "Concept"


async def test_persist_pipeline_results_links_evidence() -> None:
    report = build_report()
    repository = MagicMock()
    repository.insert_report_sections = AsyncMock(return_value=["section-id"])
    repository.insert_report_section_source_transcription = AsyncMock()
    repository.insert_report_section_source_image = AsyncMock()
    segment_id = uuid4()
    image_id = uuid4()
    template_sections = [
        TemplateSection(id="conclusie", label="Conclusie", order=1, render_type="text_block")
    ]
    generated_sections = [
        GeneratedReportSection(
            id="conclusie",
            generated_content="Concept",
            confidence_level="high",
            confidence_score=0.9,
        )
    ]

    await generation.persist_pipeline_results(
        repository,
        report,
        template_sections,
        generated_sections,
        [StoredTranscriptionSegment(id=segment_id, text="Segment")],
        [StoredImageAnalysis(id=image_id, analysis_text="Image")],
    )

    repository.insert_report_sections.assert_awaited_once()
    repository.insert_report_section_source_transcription.assert_awaited_once_with(
        "section-id",
        str(segment_id),
    )
    repository.insert_report_section_source_image.assert_awaited_once_with(
        "section-id",
        str(image_id),
    )


async def test_persist_pipeline_results_skips_unknown_section_ids() -> None:
    report = build_report()
    repository = MagicMock()
    repository.insert_report_sections = AsyncMock(return_value=[])
    repository.insert_report_section_source_transcription = AsyncMock()
    repository.insert_report_section_source_image = AsyncMock()

    await generation.persist_pipeline_results(
        repository,
        report,
        [TemplateSection(id="conclusie", label="Conclusie", render_type="text_block")],
        [
            GeneratedReportSection(
                id="unknown",
                generated_content="Concept",
                confidence_level="high",
                confidence_score=0.9,
            )
        ],
        [],
        [],
    )

    repository.insert_report_sections.assert_awaited_once_with(
        str(report.id),
        str(report.company_id),
        [],
    )
    repository.insert_report_section_source_transcription.assert_not_awaited()
    repository.insert_report_section_source_image.assert_not_awaited()
