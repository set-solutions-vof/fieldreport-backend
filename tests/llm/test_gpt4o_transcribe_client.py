from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.llm import gpt4o_transcribe_client
from src.models.reports.transcription import AudioChunk


class TemporaryDirectoryContext:
    def __init__(self, directory_name: str):
        self.directory_name = directory_name

    def __enter__(self) -> str:
        return self.directory_name

    def __exit__(self, *args: object) -> None:
        return None


async def test_transcribe_audio_returns_single_segment_from_text() -> None:
    response = SimpleNamespace(text="Volledige transcriptie")
    client = SimpleNamespace(
        audio=SimpleNamespace(
            transcriptions=SimpleNamespace(create=AsyncMock(return_value=response))
        )
    )

    with (
        patch.object(gpt4o_transcribe_client, "get_gpt4o_transcribe_client", return_value=client),
        patch.object(
            gpt4o_transcribe_client.settings,
            "gpt4o_transcribe_deployment",
            "gpt-4o-transcribe",
        ),
        patch.object(
            gpt4o_transcribe_client,
            "split_audio_sync",
            return_value=[
                AudioChunk(filename="audio.m4a", content=b"audio", duration_seconds=12.5)
            ],
        ),
    ):
        result = await gpt4o_transcribe_client.transcribe_audio(b"audio", "audio.m4a")

    assert result.full_text == "Volledige transcriptie"
    assert result.duration_seconds == 12.5
    assert len(result.segments) == 1
    assert result.segments[0].text == "Volledige transcriptie"
    assert result.segments[0].start_seconds == 0.0
    assert result.segments[0].end_seconds == 12.5
    client.audio.transcriptions.create.assert_awaited_once_with(
        model="gpt-4o-transcribe",
        file=("audio.m4a", b"audio"),
        language="nl",
        response_format="json",
    )


async def test_transcribe_audio_uses_json_for_gpt_4o_transcribe() -> None:
    response = SimpleNamespace(text="Transcriptie")
    client = SimpleNamespace(
        audio=SimpleNamespace(
            transcriptions=SimpleNamespace(create=AsyncMock(return_value=response))
        )
    )

    with (
        patch.object(gpt4o_transcribe_client, "get_gpt4o_transcribe_client", return_value=client),
        patch.object(
            gpt4o_transcribe_client.settings,
            "gpt4o_transcribe_deployment",
            "gpt-4o-transcribe",
        ),
        patch.object(
            gpt4o_transcribe_client,
            "split_audio_sync",
            return_value=[AudioChunk(filename="audio.m4a", content=b"audio", duration_seconds=5.0)],
        ),
    ):
        result = await gpt4o_transcribe_client.transcribe_audio(b"audio", "audio.m4a")

    assert result.full_text == "Transcriptie"
    assert result.duration_seconds == 5.0
    assert result.segments[0].text == "Transcriptie"
    client.audio.transcriptions.create.assert_awaited_once()
    assert client.audio.transcriptions.create.await_args.kwargs["response_format"] == "json"


async def test_transcribe_audio_merges_chunk_results() -> None:
    responses = [
        SimpleNamespace(text="Eerste chunk"),
        SimpleNamespace(text="Tweede chunk"),
    ]
    client = SimpleNamespace(
        audio=SimpleNamespace(
            transcriptions=SimpleNamespace(create=AsyncMock(side_effect=responses))
        )
    )

    with (
        patch.object(gpt4o_transcribe_client, "get_gpt4o_transcribe_client", return_value=client),
        patch.object(
            gpt4o_transcribe_client,
            "split_audio_sync",
            return_value=[
                AudioChunk(filename="chunk_000.m4a", content=b"first", duration_seconds=10.0),
                AudioChunk(filename="chunk_001.m4a", content=b"second", duration_seconds=8.0),
            ],
        ),
    ):
        result = await gpt4o_transcribe_client.transcribe_audio(b"audio", "audio.m4a")

    assert result.full_text == "Eerste chunk\n\nTweede chunk"
    assert result.duration_seconds == 18.0
    assert [segment.segment_index for segment in result.segments] == [0, 1]
    assert result.segments[0].start_seconds == 0.0
    assert result.segments[0].end_seconds == 10.0
    assert result.segments[1].start_seconds == 10.0
    assert result.segments[1].end_seconds == 18.0


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
            gpt4o_transcribe_client.tempfile,
            "TemporaryDirectory",
            return_value=TemporaryDirectoryContext(str(tmp_path)),
        ),
        patch.object(
            gpt4o_transcribe_client.subprocess,
            "run",
            side_effect=run_subprocess,
        ) as run,
    ):
        chunks = gpt4o_transcribe_client.split_audio_sync(b"input", "audio.m4a")

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
            gpt4o_transcribe_client.tempfile,
            "TemporaryDirectory",
            return_value=TemporaryDirectoryContext(str(tmp_path)),
        ),
        patch.object(
            gpt4o_transcribe_client.subprocess,
            "run",
            side_effect=run_subprocess,
        ) as run,
    ):
        chunks = gpt4o_transcribe_client.split_audio_sync(b"input", "audio")

    assert chunks == [
        AudioChunk(filename="chunk_000.m4a", content=b"reencoded", duration_seconds=6.5)
    ]
    assert run.call_count == 3
