from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.db.report_pipeline_repository import ReportPipelineRepository
from src.models.reports.generation import GeneratedReportSection
from src.models.reports.metadata import ReportMetadata
from src.models.reports.pipeline import (
    InspectionMediaFile,
    ReportPipelineContext,
    StoredImageAnalysis,
    StoredTranscriptionSegment,
)
from src.models.reports.transcription import TranscriptionResult, TranscriptionSegment
from src.models.templates.domain import (
    TemplateScalarMetadataField,
    TemplateSection,
    TemplateSelectMetadataField,
    TemplateStructure,
)
from src.pipelines import audio_pipeline


def build_report(status: str = "generating") -> ReportPipelineContext:
    return ReportPipelineContext(
        id=uuid4(),
        inspection_id=uuid4(),
        company_id=uuid4(),
        template_id=uuid4(),
        status=status,
        extra_context="Extra",
        metadata={
            "type_onderzoek": "Lekdetectie",
            "type_klant": "Zakelijk",
        },
    )


def build_pipeline_connection() -> MagicMock:
    connection = MagicMock()
    transaction = MagicMock()
    transaction.__aenter__ = AsyncMock(return_value=None)
    transaction.__aexit__ = AsyncMock(return_value=None)
    connection.transaction = MagicMock(return_value=transaction)
    return connection


async def test_run_audio_pipeline_processes_media_and_persists_sections() -> None:
    report = build_report()
    segment_id = uuid4()
    image_id = uuid4()
    template_structure = TemplateStructure(
        metadata_fields=[
            TemplateSelectMetadataField(
                key="type_onderzoek",
                label="Type onderzoek",
                type="select",
                options=["Lekdetectie"],
            ),
            TemplateScalarMetadataField(
                key="type_klant",
                label="Type klant",
                type="text",
            ),
        ],
        sections=[
            TemplateSection(
                id="conclusie",
                label="Conclusie",
                order=1,
                render_type="text_block",
            )
        ],
    )
    transcription_result = TranscriptionResult(
        full_text="Inspecteur noemt vocht.",
        duration_seconds=5.0,
        segments=[
            TranscriptionSegment(
                segment_index=0,
                start_seconds=0.0,
                end_seconds=5.0,
                text="Inspecteur noemt vocht.",
            )
        ],
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
        ],
        usage=SimpleNamespace(total_tokens=123),
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=response)))
    )
    generated_section = GeneratedReportSection(
        id="conclusie",
        generated_content="Concept",
        confidence_level="high",
        confidence_score=0.9,
    )
    connection = build_pipeline_connection()
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    with (
        patch.object(
            audio_pipeline.report_queries,
            "get_report_for_pipeline",
            AsyncMock(return_value=report),
        ),
        patch.object(
            audio_pipeline.template_queries,
            "fetch_template_structure",
            AsyncMock(return_value=template_structure),
        ),
        patch("src.pipelines.audio_pipeline.get_pool", return_value=pool),
        patch.object(
            audio_pipeline.inspection_queries,
            "fetch_inspection_audio_files",
            AsyncMock(
                return_value=[
                    InspectionMediaFile(
                        storage_key="/tmp/audio.m4a",
                        original_file_name="audio.m4a",
                    )
                ]
            ),
        ),
        patch.object(
            audio_pipeline.inspection_queries,
            "fetch_inspection_photo_files",
            AsyncMock(
                return_value=[
                    InspectionMediaFile(
                        storage_key="/tmp/photo.jpg",
                        original_file_name="photo.jpg",
                    )
                ]
            ),
        ),
        patch.object(
            audio_pipeline.blob,
            "download_file",
            side_effect=[b"audio", b"photo"],
        ),
        patch.object(
            audio_pipeline.gpt4o_transcribe_client,
            "transcribe_audio",
            AsyncMock(return_value=transcription_result),
        ),
        patch.object(
            ReportPipelineRepository,
            "insert_transcription",
            AsyncMock(return_value="transcription-id"),
        ),
        patch.object(
            ReportPipelineRepository,
            "insert_transcription_segments",
            AsyncMock(return_value=["segment-id"]),
        ),
        patch.object(
            audio_pipeline.gpt4o_client,
            "analyze_inspection_photo",
            AsyncMock(return_value="Fotoanalyse"),
        ),
        patch.object(
            ReportPipelineRepository,
            "insert_image_analysis",
            AsyncMock(return_value="image-id"),
        ),
        patch.object(
            ReportPipelineRepository,
            "fetch_transcription_segments_for_inspection",
            AsyncMock(
                return_value=[
                    StoredTranscriptionSegment(
                        id=segment_id,
                        text="Inspecteur noemt vocht.",
                    )
                ]
            ),
        ),
        patch.object(
            ReportPipelineRepository,
            "fetch_image_analyses_for_inspection",
            AsyncMock(return_value=[StoredImageAnalysis(id=image_id, analysis_text="Fotoanalyse")]),
        ),
        patch.object(audio_pipeline.client_factory, "get_gpt4o_client", return_value=client),
        patch.object(
            ReportPipelineRepository,
            "insert_report_section",
            AsyncMock(return_value="section-id"),
        ) as insert_section,
        patch.object(
            ReportPipelineRepository,
            "insert_report_section_source_transcription",
            AsyncMock(),
        ) as insert_segment_source,
        patch.object(
            ReportPipelineRepository,
            "insert_report_section_source_image",
            AsyncMock(),
        ) as insert_image_source,
        patch.object(audio_pipeline.report_queries, "set_report_status", AsyncMock()) as set_status,
    ):
        await audio_pipeline.run_audio_pipeline("report-id")

    insert_section.assert_awaited_once()
    assert insert_section.await_args.args[0] == str(report.id)
    assert insert_section.await_args.args[1] == str(report.company_id)
    assert insert_section.await_args.args[2] == generated_section
    insert_segment_source.assert_awaited_once_with("section-id", str(segment_id))
    insert_image_source.assert_awaited_once_with("section-id", str(image_id))
    set_status.assert_awaited_once_with("report-id", "draft")


async def test_run_audio_pipeline_marks_failed_when_media_file_fails() -> None:
    report = build_report()
    template_structure = TemplateStructure(
        sections=[TemplateSection(id="conclusie", label="Conclusie", render_type="text_block")]
    )
    connection = build_pipeline_connection()
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    with (
        patch.object(
            audio_pipeline.report_queries,
            "get_report_for_pipeline",
            AsyncMock(return_value=report),
        ),
        patch.object(
            audio_pipeline.template_queries,
            "fetch_template_structure",
            AsyncMock(return_value=template_structure),
        ),
        patch("src.pipelines.audio_pipeline.get_pool", return_value=pool),
        patch.object(
            audio_pipeline.inspection_queries,
            "fetch_inspection_audio_files",
            AsyncMock(
                return_value=[
                    InspectionMediaFile(
                        storage_key="/tmp/audio.m4a",
                        original_file_name="audio.m4a",
                    )
                ]
            ),
        ),
        patch.object(
            audio_pipeline.inspection_queries,
            "fetch_inspection_photo_files",
            AsyncMock(return_value=[]),
        ),
        patch.object(
            audio_pipeline.blob,
            "download_file",
            side_effect=ValueError("missing file"),
        ),
        patch.object(audio_pipeline.report_queries, "set_report_status", AsyncMock()) as set_status,
    ):
        with pytest.raises(ValueError, match="missing file"):
            await audio_pipeline.run_audio_pipeline("report-id")

    set_status.assert_awaited_once_with("report-id", "failed")


async def test_run_audio_pipeline_marks_failed_when_report_generation_fails() -> None:
    report = build_report()
    template_structure = TemplateStructure(
        sections=[TemplateSection(id="conclusie", label="Conclusie", render_type="text_block")]
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=AsyncMock(side_effect=ValueError("bad")))
        )
    )
    connection = build_pipeline_connection()
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    with (
        patch.object(
            audio_pipeline.report_queries,
            "get_report_for_pipeline",
            AsyncMock(return_value=report),
        ),
        patch.object(
            audio_pipeline.template_queries,
            "fetch_template_structure",
            AsyncMock(return_value=template_structure),
        ),
        patch("src.pipelines.audio_pipeline.get_pool", return_value=pool),
        patch.object(
            audio_pipeline.inspection_queries,
            "fetch_inspection_audio_files",
            AsyncMock(return_value=[]),
        ),
        patch.object(
            audio_pipeline.inspection_queries,
            "fetch_inspection_photo_files",
            AsyncMock(return_value=[]),
        ),
        patch.object(
            ReportPipelineRepository,
            "fetch_transcription_segments_for_inspection",
            AsyncMock(return_value=[]),
        ),
        patch.object(
            ReportPipelineRepository,
            "fetch_image_analyses_for_inspection",
            AsyncMock(return_value=[]),
        ),
        patch.object(audio_pipeline.client_factory, "get_gpt4o_client", return_value=client),
        patch.object(audio_pipeline.report_queries, "set_report_status", AsyncMock()) as set_status,
    ):
        with pytest.raises(ValueError, match="bad"):
            await audio_pipeline.run_audio_pipeline("report-id")

    set_status.assert_awaited_once_with("report-id", "failed")


def test_build_report_generation_prompt_includes_metadata_and_extra_context() -> None:
    report = build_report()
    template_structure = TemplateStructure(
        metadata_fields=[
            TemplateScalarMetadataField(key="type_klant", label="Type klant", type="text")
        ],
        sections=[TemplateSection(id="conclusie", label="Conclusie", render_type="text_block")],
    )

    prompt = audio_pipeline.build_report_generation_prompt(
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

    prompt = audio_pipeline.build_report_generation_prompt(
        template_structure,
        template_structure.sections,
        [],
        [],
        report,
    )

    assert "Extra context:" not in prompt


async def test_transcribe_inspection_audio_files_persists_transcription() -> None:
    report = build_report()
    repository = MagicMock()
    repository.insert_transcription = AsyncMock(return_value="transcription-id")
    repository.insert_transcription_segments = AsyncMock(return_value=["segment-id"])
    transcription_result = TranscriptionResult(
        full_text="Tekst",
        duration_seconds=1.0,
        segments=[
            TranscriptionSegment(
                segment_index=0,
                start_seconds=0.0,
                end_seconds=1.0,
                text="Tekst",
            )
        ],
    )

    with (
        patch.object(
            audio_pipeline.inspection_queries,
            "fetch_inspection_audio_files",
            AsyncMock(
                return_value=[
                    InspectionMediaFile(
                        storage_key="/tmp/audio.m4a",
                        original_file_name="audio.m4a",
                    )
                ]
            ),
        ),
        patch.object(
            audio_pipeline.blob,
            "download_file",
            return_value=b"audio",
        ),
        patch.object(
            audio_pipeline.gpt4o_transcribe_client,
            "transcribe_audio",
            AsyncMock(return_value=transcription_result),
        ),
    ):
        await audio_pipeline.transcribe_inspection_audio_files(report, repository)

    repository.insert_transcription.assert_awaited_once()
    repository.insert_transcription_segments.assert_awaited_once()


async def test_analyze_inspection_photo_files_persists_analysis() -> None:
    report = build_report()
    repository = MagicMock()
    repository.insert_image_analysis = AsyncMock(return_value="image-id")

    with (
        patch.object(
            audio_pipeline.inspection_queries,
            "fetch_inspection_photo_files",
            AsyncMock(
                return_value=[
                    InspectionMediaFile(
                        storage_key="/tmp/photo.jpg",
                        original_file_name="photo.jpg",
                    )
                ]
            ),
        ),
        patch.object(
            audio_pipeline.blob,
            "download_file",
            return_value=b"photo",
        ),
        patch.object(
            audio_pipeline.gpt4o_client,
            "analyze_inspection_photo",
            AsyncMock(return_value="Fotoanalyse"),
        ),
    ):
        await audio_pipeline.analyze_inspection_photo_files(report, repository)

    repository.insert_image_analysis.assert_awaited_once()


async def test_analyze_inspection_photo_files_raises_when_photo_analysis_fails() -> None:
    report = build_report()
    repository = MagicMock()

    with (
        patch.object(
            audio_pipeline.inspection_queries,
            "fetch_inspection_photo_files",
            AsyncMock(
                return_value=[
                    InspectionMediaFile(
                        storage_key="/tmp/photo.jpg",
                        original_file_name="photo.jpg",
                    )
                ]
            ),
        ),
        patch.object(
            audio_pipeline.blob,
            "download_file",
            side_effect=ValueError("missing photo"),
        ),
    ):
        with pytest.raises(ValueError, match="missing photo"):
            await audio_pipeline.analyze_inspection_photo_files(report, repository)


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

    with patch.object(audio_pipeline.client_factory, "get_gpt4o_client", return_value=client):
        sections = await audio_pipeline.generate_report_sections(
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
    repository.insert_report_section = AsyncMock(return_value="section-id")
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

    await audio_pipeline.persist_pipeline_results(
        repository,
        report,
        template_sections,
        generated_sections,
        [StoredTranscriptionSegment(id=segment_id, text="Segment")],
        [StoredImageAnalysis(id=image_id, analysis_text="Image")],
    )

    repository.insert_report_section.assert_awaited_once()
    repository.insert_report_section_source_transcription.assert_awaited_once_with(
        "section-id",
        str(segment_id),
    )
    repository.insert_report_section_source_image.assert_awaited_once_with(
        "section-id",
        str(image_id),
    )
