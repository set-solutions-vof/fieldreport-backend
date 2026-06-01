import asyncio
import subprocess
import tempfile
from pathlib import Path

from src.config import settings
from src.llm.client_factory import get_gpt4o_transcribe_client
from src.models.reports.transcription import (
    AudioChunk,
    ChunkTranscription,
    TranscriptionResult,
    TranscriptionSegment,
)

AUDIO_CHUNK_SECONDS = 1200.0


async def transcribe_audio(
    file_content: bytes,
    filename: str,
    language: str = "nl",
) -> TranscriptionResult:
    client = get_gpt4o_transcribe_client()
    audio_chunks = await asyncio.to_thread(split_audio_sync, file_content, filename)
    chunk_transcriptions: list[ChunkTranscription] = []

    for audio_chunk in audio_chunks:
        response = await client.audio.transcriptions.create(
            model=settings.gpt4o_transcribe_deployment,
            file=(audio_chunk.filename, audio_chunk.content),
            language=language,
            response_format="json",
        )
        chunk_transcriptions.append(
            ChunkTranscription(
                text=response.text,
                duration_seconds=audio_chunk.duration_seconds,
            )
        )

    return merge_chunk_transcriptions(chunk_transcriptions)


def merge_chunk_transcriptions(
    chunk_transcriptions: list[ChunkTranscription],
) -> TranscriptionResult:
    segments: list[TranscriptionSegment] = []
    offset_seconds = 0.0
    full_text_parts: list[str] = []
    total_duration_seconds = 0.0

    for chunk_transcription in chunk_transcriptions:
        full_text_parts.append(chunk_transcription.text)
        segments.append(
            TranscriptionSegment(
                segment_index=len(segments),
                start_seconds=offset_seconds,
                end_seconds=offset_seconds + chunk_transcription.duration_seconds,
                text=chunk_transcription.text,
            )
        )
        offset_seconds += chunk_transcription.duration_seconds
        total_duration_seconds += chunk_transcription.duration_seconds

    return TranscriptionResult(
        full_text="\n\n".join(full_text_parts),
        duration_seconds=total_duration_seconds,
        segments=segments,
    )


def split_audio_sync(file_content: bytes, filename: str) -> list[AudioChunk]:
    file_extension = Path(filename).suffix or ".m4a"

    with tempfile.TemporaryDirectory() as directory_name:
        directory = Path(directory_name)
        input_path = directory / f"input{file_extension}"
        output_pattern = directory / f"chunk_%03d{file_extension}"
        input_path.write_bytes(file_content)

        subprocess_result = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(input_path),
                "-f",
                "segment",
                "-segment_time",
                str(int(AUDIO_CHUNK_SECONDS)),
                "-reset_timestamps",
                "1",
                "-map",
                "0:a",
                "-c",
                "copy",
                str(output_pattern),
            ],
            check=False,
            capture_output=True,
        )

        if subprocess_result.returncode != 0:
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(input_path),
                    "-f",
                    "segment",
                    "-segment_time",
                    str(int(AUDIO_CHUNK_SECONDS)),
                    "-reset_timestamps",
                    "1",
                    "-map",
                    "0:a",
                    "-vn",
                    str(output_pattern),
                ],
                check=True,
                capture_output=True,
            )

        audio_chunks: list[AudioChunk] = []

        for chunk_path in sorted(directory.glob(f"chunk_*{file_extension}")):
            ffprobe_result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(chunk_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            audio_chunks.append(
                AudioChunk(
                    filename=chunk_path.name,
                    content=chunk_path.read_bytes(),
                    duration_seconds=float(ffprobe_result.stdout.strip()),
                )
            )

        return audio_chunks
