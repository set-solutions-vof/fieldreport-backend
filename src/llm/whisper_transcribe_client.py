import asyncio
import subprocess
import tempfile
from pathlib import Path

from src.config import settings
from src.exceptions.transcription_segments_missing import TranscriptionSegmentsMissing
from src.llm.client_factory import get_whisper_transcribe_client
from src.models.reports.transcription import AudioChunk, TranscriptionResult, TranscriptionSegment

AUDIO_CHUNK_SECONDS = 1200.0
MIN_SEGMENT_SECONDS = 15.0
MAX_SEGMENT_SECONDS = 45.0


async def transcribe_audio(
    file_content: bytes,
    filename: str,
    language: str = "nl",
) -> TranscriptionResult:
    audio_chunks = await asyncio.to_thread(split_audio_sync, file_content, filename)
    return await transcribe_audio_chunks(audio_chunks, language)


async def transcribe_audio_chunks(
    audio_chunks: list[AudioChunk],
    language: str,
) -> TranscriptionResult:
    client = get_whisper_transcribe_client()
    segments: list[TranscriptionSegment] = []
    full_text_parts: list[str] = []
    offset_seconds = 0.0
    total_duration_seconds = 0.0

    for audio_chunk in audio_chunks:
        response = await client.audio.transcriptions.create(
            model=settings.whisper_deployment,
            file=(audio_chunk.filename, audio_chunk.content),
            language=language,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )
        segments.extend(
            merge_transcription_segments(
                map_response_segments(response, offset_seconds, settings.whisper_deployment)
            )
        )
        full_text_parts.append(response.text)
        offset_seconds += audio_chunk.duration_seconds
        total_duration_seconds += audio_chunk.duration_seconds

    numbered_segments = [
        TranscriptionSegment(
            segment_index=segment_index,
            start_seconds=segment.start_seconds,
            end_seconds=segment.end_seconds,
            text=segment.text,
        )
        for segment_index, segment in enumerate(segments)
    ]

    return TranscriptionResult(
        full_text="\n\n".join(full_text_parts),
        duration_seconds=total_duration_seconds,
        segments=numbered_segments,
    )


def merge_transcription_segments(
    segments: list[TranscriptionSegment],
) -> list[TranscriptionSegment]:
    if not segments:
        return []

    merged_segments: list[TranscriptionSegment] = []
    segment_index = 0

    while segment_index < len(segments):
        chunk_start_seconds = segments[segment_index].start_seconds
        chunk_texts = [segments[segment_index].text]
        chunk_end_seconds = segments[segment_index].end_seconds
        segment_index += 1

        while segment_index < len(segments):
            next_segment = segments[segment_index]
            prospective_duration = next_segment.end_seconds - chunk_start_seconds

            if prospective_duration > MAX_SEGMENT_SECONDS:
                break

            chunk_texts.append(next_segment.text)
            chunk_end_seconds = next_segment.end_seconds
            segment_index += 1
            combined_text = " ".join(chunk_texts)
            chunk_duration = chunk_end_seconds - chunk_start_seconds

            if ends_sentence(combined_text) and chunk_duration >= MIN_SEGMENT_SECONDS:
                break

        merged_segments.append(
            TranscriptionSegment(
                segment_index=0,
                start_seconds=chunk_start_seconds,
                end_seconds=chunk_end_seconds,
                text=" ".join(chunk_texts),
            )
        )

    return merged_segments


def map_response_segments(
    response: object,
    offset_seconds: float,
    model: str,
) -> list[TranscriptionSegment]:
    api_segments = getattr(response, "segments", None)
    if not api_segments:
        raise TranscriptionSegmentsMissing(model)

    return [
        TranscriptionSegment(
            segment_index=0,
            start_seconds=float(segment.start) + offset_seconds,
            end_seconds=float(segment.end) + offset_seconds,
            text=str(segment.text).strip(),
        )
        for segment in api_segments
    ]



def ends_sentence(text: str) -> bool:
    stripped = text.rstrip()
    return bool(stripped) and stripped[-1] in ".!?"

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
