from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

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
        ]
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
            audio_pipeline.inspection_file_storage,
            "load_inspection_file",
            side_effect=[b"audio", b"photo"],
        ),
        patch.object(
            audio_pipeline.gpt4o_transcribe_client,
            "transcribe_audio",
            AsyncMock(return_value=transcription_result),
        ),
        patch.object(
            audio_pipeline.report_queries,
            "insert_transcription",
            AsyncMock(return_value="transcription-id"),
        ),
        patch.object(
            audio_pipeline.report_queries,
            "insert_transcription_segments",
            AsyncMock(return_value=["segment-id"]),
        ),
        patch.object(
            audio_pipeline.gpt4o_client,
            "analyze_inspection_photo",
            AsyncMock(return_value="Fotoanalyse"),
        ),
        patch.object(
            audio_pipeline.report_queries,
            "insert_image_analysis",
            AsyncMock(return_value="image-id"),
        ),
        patch.object(
            audio_pipeline.report_queries,
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
            audio_pipeline.report_queries,
            "fetch_image_analyses_for_inspection",
            AsyncMock(return_value=[StoredImageAnalysis(id=image_id, analysis_text="Fotoanalyse")]),
        ),
        patch.object(audio_pipeline.client_factory, "get_gpt4o_client", return_value=client),
        patch.object(
            audio_pipeline.report_queries,
            "insert_report_section",
            AsyncMock(return_value="section-id"),
        ) as insert_section,
        patch.object(
            audio_pipeline.report_queries,
            "insert_report_section_source_transcription",
            AsyncMock(),
        ) as insert_segment_source,
        patch.object(
            audio_pipeline.report_queries,
            "insert_report_section_source_image",
            AsyncMock(),
        ) as insert_image_source,
        patch.object(audio_pipeline.report_queries, "set_report_status", AsyncMock()) as set_status,
    ):
        await audio_pipeline.run_audio_pipeline("report-id")

    insert_section.assert_awaited_once_with(
        "report-id",
        str(report.company_id),
        "conclusie",
        1,
        "text_block",
        "Concept",
        "high",
        0.9,
    )
    insert_segment_source.assert_awaited_once_with("section-id", str(segment_id))
    insert_image_source.assert_awaited_once_with("section-id", str(image_id))
    set_status.assert_awaited_once_with("report-id", "draft")


async def test_run_audio_pipeline_continues_after_media_file_failures() -> None:
    report = build_report()
    template_structure = TemplateStructure(
        sections=[TemplateSection(id="conclusie", label="Conclusie", render_type="text_block")]
    )
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"sections":[]}'))],
        usage=SimpleNamespace(total_tokens=1),
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=response)))
    )

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
            audio_pipeline.inspection_file_storage,
            "load_inspection_file",
            side_effect=ValueError("missing file"),
        ),
        patch.object(
            audio_pipeline.report_queries,
            "fetch_transcription_segments_for_inspection",
            AsyncMock(return_value=[]),
        ),
        patch.object(
            audio_pipeline.report_queries,
            "fetch_image_analyses_for_inspection",
            AsyncMock(return_value=[]),
        ),
        patch.object(audio_pipeline.client_factory, "get_gpt4o_client", return_value=client),
        patch.object(audio_pipeline.report_queries, "set_report_status", AsyncMock()) as set_status,
    ):
        await audio_pipeline.run_audio_pipeline("report-id")

    set_status.assert_awaited_once_with("report-id", "draft")


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
            audio_pipeline.report_queries,
            "fetch_transcription_segments_for_inspection",
            AsyncMock(return_value=[]),
        ),
        patch.object(
            audio_pipeline.report_queries,
            "fetch_image_analyses_for_inspection",
            AsyncMock(return_value=[]),
        ),
        patch.object(audio_pipeline.client_factory, "get_gpt4o_client", return_value=client),
        patch.object(audio_pipeline.report_queries, "set_report_status", AsyncMock()) as set_status,
    ):
        try:
            await audio_pipeline.run_audio_pipeline("report-id")
        except ValueError:
            raised = True
        else:
            raised = False

    assert raised is True
    set_status.assert_awaited_once_with("report-id", "failed")
