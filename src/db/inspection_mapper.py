import asyncpg

from src.models.reports.pipeline import InspectionMediaFile


def map_inspection_media_file(row: asyncpg.Record) -> InspectionMediaFile:
    return InspectionMediaFile(
        storage_key=row["storage_key"],
        original_file_name=row["original_file_name"],
    )
