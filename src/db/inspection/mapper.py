from collections.abc import Mapping

from src.models.reports.pipeline import InspectionMediaFile


def map_inspection_media_file(row: Mapping[str, object]) -> InspectionMediaFile:
    return InspectionMediaFile.model_validate(dict(row))
