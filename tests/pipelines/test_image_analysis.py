from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.reports.pipeline import InspectionMediaFile
from src.pipelines.report_generation import image_analysis
from tests.pipelines.helpers import build_report


async def test_analyze_inspection_photo_files_persists_analysis() -> None:
    report = build_report()
    repository = MagicMock()
    repository.insert_image_analysis = AsyncMock(return_value="image-id")

    with (
        patch(
            "src.pipelines.report_generation.image_analysis.fetch_inspection_photo_files",
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
            image_analysis.blob,
            "download_file",
            return_value=b"photo",
        ),
        patch.object(
            image_analysis.gpt4o_client,
            "analyze_inspection_photo",
            AsyncMock(return_value="Fotoanalyse"),
        ),
    ):
        await image_analysis.analyze_inspection_photo_files(report, repository)

    repository.insert_image_analysis.assert_awaited_once()


async def test_analyze_inspection_photo_files_raises_when_photo_analysis_fails() -> None:
    report = build_report()
    repository = MagicMock()

    with (
        patch(
            "src.pipelines.report_generation.image_analysis.fetch_inspection_photo_files",
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
            image_analysis.blob,
            "download_file",
            side_effect=ValueError("missing photo"),
        ),
    ):
        with pytest.raises(ValueError, match="missing photo"):
            await image_analysis.analyze_inspection_photo_files(report, repository)
