from io import BytesIO
from unittest.mock import AsyncMock, patch

from starlette.datastructures import UploadFile

from src.utils import storage


async def test_upload_files_uploads_all_files_and_returns_keys() -> None:
    file = UploadFile(filename="audio.m4a", file=BytesIO(b"audio"))

    with (
        patch.object(storage, "uuid4", return_value="file-id"),
        patch.object(storage.blob, "upload_form_file", AsyncMock()) as upload_form_file,
    ):
        keys = await storage.upload_files("inspections", "company/inspection/audio", [file])

    assert keys == ["company/inspection/audio/file-id.m4a"]
    upload_form_file.assert_awaited_once_with(
        "inspections",
        "company/inspection/audio/file-id.m4a",
        file,
    )


async def test_upload_images_normalizes_and_uploads_images() -> None:
    file = UploadFile(filename="photo.heic", file=BytesIO(b"image"))

    with (
        patch.object(storage, "uuid4", return_value="image-id"),
        patch.object(
            storage,
            "normalize_to_jpeg",
            return_value=(b"jpeg", ".jpg", "image/jpeg"),
        ) as normalize,
        patch.object(storage.blob, "upload_file", AsyncMock()) as upload_file,
    ):
        keys = await storage.upload_images("inspections", "company/inspection/photos", [file])

    assert keys == ["company/inspection/photos/image-id.jpg"]
    normalize.assert_called_once_with(b"image", "photo.heic", "")
    upload_file.assert_awaited_once_with(
        "inspections",
        "company/inspection/photos/image-id.jpg",
        b"jpeg",
        "image/jpeg",
    )
