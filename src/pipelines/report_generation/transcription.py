from loguru import logger

from src.db.inspection.queries import fetch_inspection_audio_files
from src.db.report.pipeline_repository import ReportPipelineRepository
from src.llm import whisper_transcribe_client
from src.models.reports.pipeline import ReportPipelineContext
from src.storage import blob


async def transcribe_inspection_audio_files(
    report: ReportPipelineContext,
    repository: ReportPipelineRepository,
) -> None:
    audio_files = await fetch_inspection_audio_files(str(report.inspection_id))

    for audio_file in audio_files:
        audio_key = audio_file.storage_key
        try:
            file_content = (await blob.download_file("inspections", audio_key))[0]
            result = await whisper_transcribe_client.transcribe_audio(
                file_content,
                audio_file.original_file_name,
            )
            transcription_id = await repository.insert_transcription(
                str(report.inspection_id),
                str(report.company_id),
                audio_key,
                result.full_text,
                result.duration_seconds,
            )
            segment_ids = await repository.insert_transcription_segments(
                transcription_id,
                str(report.inspection_id),
                result.segments,
            )
            logger.info(
                "Transcribed {} into {} segment(s), duration={}s, chars={}",
                audio_key,
                len(segment_ids),
                result.duration_seconds,
                len(result.full_text),
            )
        except Exception:
            logger.exception("Audio file {} failed", audio_key)
            raise
