from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.exceptions.transcription_segments_missing import TranscriptionSegmentsMissing
from src.llm import whisper_transcribe_client
from src.models.reports.transcription import AudioChunk, TranscriptionSegment


def verbose_response(text: str, segments: list[dict[str, object]]) -> SimpleNamespace:
    return SimpleNamespace(
        text=text,
        segments=[SimpleNamespace(**segment) for segment in segments],
    )


async def test_transcribe_audio_maps_whisper_segments() -> None:
    response = verbose_response(
        "Volledige transcriptie",
        [
            {"start": 0.0, "end": 4.0, "text": "Eerste zin."},
            {"start": 4.0, "end": 12.5, "text": "Tweede zin."},
        ],
    )
    client = SimpleNamespace(
        audio=SimpleNamespace(
            transcriptions=SimpleNamespace(create=AsyncMock(return_value=response))
        )
    )

    with (
        patch.object(
            whisper_transcribe_client,
            "get_whisper_transcribe_client",
            return_value=client,
        ),
        patch.object(whisper_transcribe_client.settings, "whisper_deployment", "whisper"),
        patch.object(
            whisper_transcribe_client,
            "split_audio_sync",
            return_value=[
                AudioChunk(filename="audio.m4a", content=b"audio", duration_seconds=12.5)
            ],
        ),
    ):
        result = await whisper_transcribe_client.transcribe_audio(b"audio", "audio.m4a")

    assert result.full_text == "Volledige transcriptie"
    assert result.duration_seconds == 12.5
    assert len(result.segments) == 1
    assert result.segments[0].text == "Eerste zin. Tweede zin."
    assert result.segments[0].start_seconds == 0.0
    assert result.segments[0].end_seconds == 12.5
    client.audio.transcriptions.create.assert_awaited_once_with(
        model="whisper",
        file=("audio.m4a", b"audio"),
        language="nl",
        response_format="verbose_json",
        timestamp_granularities=["segment"],
    )


async def test_transcribe_audio_raises_when_whisper_response_has_no_segments() -> None:
    response = SimpleNamespace(text="Alleen tekst")
    client = SimpleNamespace(
        audio=SimpleNamespace(
            transcriptions=SimpleNamespace(create=AsyncMock(return_value=response))
        )
    )

    with (
        patch.object(
            whisper_transcribe_client,
            "get_whisper_transcribe_client",
            return_value=client,
        ),
        patch.object(whisper_transcribe_client.settings, "whisper_deployment", "whisper"),
        patch.object(
            whisper_transcribe_client,
            "split_audio_sync",
            return_value=[AudioChunk(filename="audio.m4a", content=b"audio", duration_seconds=5.0)],
        ),
        pytest.raises(TranscriptionSegmentsMissing),
    ):
        await whisper_transcribe_client.transcribe_audio(b"audio", "audio.m4a")


async def test_transcribe_audio_offsets_whisper_segments_for_later_chunks() -> None:
    responses = [
        verbose_response(
            "Eerste chunk",
            [{"start": 0.0, "end": 10.0, "text": "Eerste chunk."}],
        ),
        verbose_response(
            "Tweede chunk",
            [{"start": 0.0, "end": 8.0, "text": "Tweede chunk."}],
        ),
    ]
    client = SimpleNamespace(
        audio=SimpleNamespace(
            transcriptions=SimpleNamespace(create=AsyncMock(side_effect=responses))
        )
    )

    with (
        patch.object(
            whisper_transcribe_client,
            "get_whisper_transcribe_client",
            return_value=client,
        ),
        patch.object(whisper_transcribe_client.settings, "whisper_deployment", "whisper"),
        patch.object(
            whisper_transcribe_client,
            "split_audio_sync",
            return_value=[
                AudioChunk(filename="chunk_000.m4a", content=b"first", duration_seconds=10.0),
                AudioChunk(filename="chunk_001.m4a", content=b"second", duration_seconds=8.0),
            ],
        ),
    ):
        result = await whisper_transcribe_client.transcribe_audio(b"audio", "audio.m4a")

    assert result.full_text == "Eerste chunk\n\nTweede chunk"
    assert result.duration_seconds == 18.0
    assert [segment.segment_index for segment in result.segments] == [0, 1]
    assert result.segments[0].start_seconds == 0.0
    assert result.segments[0].end_seconds == 10.0
    assert result.segments[1].start_seconds == 10.0
    assert result.segments[1].end_seconds == 18.0


def test_merge_transcription_segments_merges_short_segments_until_sentence_end() -> None:
    segments = [
        TranscriptionSegment(
            segment_index=0,
            start_seconds=0.0,
            end_seconds=4.0,
            text="Hier spreekt Henk.",
        ),
        TranscriptionSegment(
            segment_index=0,
            start_seconds=4.0,
            end_seconds=9.0,
            text="We zijn op locatie.",
        ),
        TranscriptionSegment(
            segment_index=0,
            start_seconds=9.0,
            end_seconds=12.0,
            text="Het onderzoek start nu.",
        ),
    ]

    merged_segments = whisper_transcribe_client.merge_transcription_segments(segments)

    assert len(merged_segments) == 1
    assert merged_segments[0].start_seconds == 0.0
    assert merged_segments[0].end_seconds == 12.0
    assert "Hier spreekt Henk." in merged_segments[0].text


def test_merge_transcription_segments_splits_before_exceeding_maximum_duration() -> None:
    segments = [
        TranscriptionSegment(
            segment_index=0,
            start_seconds=0.0,
            end_seconds=20.0,
            text="Eerste alinea voltooid.",
        ),
        TranscriptionSegment(
            segment_index=0,
            start_seconds=20.0,
            end_seconds=55.0,
            text="Tweede alinea voltooid.",
        ),
    ]

    merged_segments = whisper_transcribe_client.merge_transcription_segments(segments)

    assert len(merged_segments) == 2
    assert merged_segments[0].end_seconds == 20.0
    assert merged_segments[1].start_seconds == 20.0


def test_merge_transcription_segments_respects_maximum_duration() -> None:
    segments = [
        TranscriptionSegment(
            segment_index=0,
            start_seconds=index * 10.0,
            end_seconds=(index + 1) * 10.0,
            text=f"Zin {index}.",
        )
        for index in range(6)
    ]

    merged_segments = whisper_transcribe_client.merge_transcription_segments(segments)

    assert len(merged_segments) < len(segments)
    assert all(
        segment.end_seconds - segment.start_seconds <= 45.0 for segment in merged_segments
    )


def test_map_response_segments_maps_api_segments() -> None:
    response = SimpleNamespace(
        segments=[
            SimpleNamespace(start=1.5, end=3.0, text=" tekst "),
        ]
    )

    segments = whisper_transcribe_client.map_response_segments(response, 10.0, "whisper")

    assert len(segments) == 1
    assert segments[0].start_seconds == 11.5
    assert segments[0].end_seconds == 13.0
    assert segments[0].text == "tekst"


def test_split_audio_sync_returns_chunk_files(tmp_path) -> None:
    def run_subprocess(command: list[str], **kwargs):
        if command[0] == "ffmpeg":
            (tmp_path / "chunk_000.m4a").write_bytes(b"first")
            (tmp_path / "chunk_001.m4a").write_bytes(b"second")
            return SimpleNamespace(returncode=0)

        if command[0] == "ffprobe":
            if command[-1].endswith("chunk_000.m4a"):
                return SimpleNamespace(stdout="10.0\n", returncode=0)

            return SimpleNamespace(stdout="8.0\n", returncode=0)

        raise AssertionError(f"Unexpected command: {command[0]}")

    with (
        patch.object(
            whisper_transcribe_client.tempfile,
            "TemporaryDirectory",
            return_value=nullcontext(str(tmp_path)),
        ),
        patch.object(
            whisper_transcribe_client.subprocess,
            "run",
            side_effect=run_subprocess,
        ) as run,
    ):
        chunks = whisper_transcribe_client.split_audio_sync(b"input", "audio.m4a")

    assert chunks == [
        AudioChunk(filename="chunk_000.m4a", content=b"first", duration_seconds=10.0),
        AudioChunk(filename="chunk_001.m4a", content=b"second", duration_seconds=8.0),
    ]
    assert run.call_count == 3


def test_split_audio_sync_reencodes_when_stream_copy_fails(tmp_path) -> None:
    ffmpeg_calls = 0

    def run_subprocess(command: list[str], **kwargs):
        nonlocal ffmpeg_calls

        if command[0] == "ffmpeg":
            if ffmpeg_calls == 0:
                ffmpeg_calls += 1
                return SimpleNamespace(returncode=1)

            (tmp_path / "chunk_000.m4a").write_bytes(b"reencoded")
            return SimpleNamespace(returncode=0)

        if command[0] == "ffprobe":
            return SimpleNamespace(stdout="6.5\n", returncode=0)

        raise AssertionError(f"Unexpected command: {command[0]}")

    with (
        patch.object(
            whisper_transcribe_client.tempfile,
            "TemporaryDirectory",
            return_value=nullcontext(str(tmp_path)),
        ),
        patch.object(
            whisper_transcribe_client.subprocess,
            "run",
            side_effect=run_subprocess,
        ) as run,
    ):
        chunks = whisper_transcribe_client.split_audio_sync(b"input", "audio")

    assert chunks == [
        AudioChunk(filename="chunk_000.m4a", content=b"reencoded", duration_seconds=6.5)
    ]
    assert run.call_count == 3
