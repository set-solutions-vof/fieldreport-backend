from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.reports.pipeline import InspectionMediaFile
from src.models.reports.transcription import TranscriptionResult, TranscriptionSegment
from src.pipelines.report_generation import transcription
from tests.pipelines.helpers import build_report


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
        patch(
            "src.pipelines.report_generation.transcription.fetch_inspection_audio_files",
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
            transcription.blob,
            "download_file",
            return_value=(b"audio", "audio/mpeg"),
        ),
        patch.object(
            transcription.whisper_transcribe_client,
            "transcribe_audio",
            AsyncMock(return_value=transcription_result),
        ),
    ):
        await transcription.transcribe_inspection_audio_files(report, repository)

    repository.insert_transcription.assert_awaited_once()
    repository.insert_transcription_segments.assert_awaited_once()


async def test_transcribe_inspection_audio_files_raises_when_transcription_fails() -> None:
    report = build_report()
    repository = MagicMock()

    with (
        patch(
            "src.pipelines.report_generation.transcription.fetch_inspection_audio_files",
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
            transcription.blob,
            "download_file",
            side_effect=ValueError("missing audio"),
        ),
    ):
        with pytest.raises(ValueError, match="missing audio"):
            await transcription.transcribe_inspection_audio_files(report, repository)
