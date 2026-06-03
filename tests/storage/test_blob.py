from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.datastructures import UploadFile

from src.storage import blob


async def test_upload_form_file_uploads_blob_and_returns_url() -> None:
    upload_file = UploadFile(filename="logo.png", file=BytesIO(b"data"))

    with patch.object(
        blob, "upload_file", AsyncMock(return_value="https://storage.example/blob")
    ) as upload:
        url = await blob.upload_form_file("logos", "key.png", upload_file)

    assert url == "https://storage.example/blob"
    upload.assert_awaited_once_with("logos", "key.png", b"data", "application/octet-stream")


async def test_upload_file_uploads_blob_and_returns_url() -> None:
    blob_client = MagicMock()
    blob_client.upload_blob = AsyncMock()
    blob_client.url = "https://storage.example/logos/key.png"
    service = MagicMock()
    service.get_blob_client.return_value = blob_client
    service.__aenter__ = AsyncMock(return_value=service)
    service.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "src.storage.blob.BlobServiceClient.from_connection_string",
        return_value=service,
    ):
        url = await blob.upload_file("logos", "key.png", b"data", "image/png")

    assert url == "https://storage.example/logos/key.png"
    blob_client.upload_blob.assert_awaited_once()


async def test_ensure_containers_creates_missing_containers() -> None:
    existing = MagicMock()
    existing.exists = AsyncMock(return_value=True)
    existing.create_container = AsyncMock()
    missing = MagicMock()
    missing.exists = AsyncMock(return_value=False)
    missing.create_container = AsyncMock()
    missing_logos = MagicMock()
    missing_logos.exists = AsyncMock(return_value=False)
    missing_logos.create_container = AsyncMock()
    service = MagicMock()
    service.get_container_client.side_effect = [existing, missing, missing_logos]
    service.__aenter__ = AsyncMock(return_value=service)
    service.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "src.storage.blob.BlobServiceClient.from_connection_string",
        return_value=service,
    ):
        await blob.ensure_containers()

    existing.create_container.assert_not_awaited()
    missing.create_container.assert_awaited_once_with()
    missing_logos.create_container.assert_awaited_once_with(public_access="blob")


async def test_download_file_returns_bytes() -> None:
    blob_client = MagicMock()
    stream = MagicMock()
    stream.readall = AsyncMock(return_value=b"file-content")
    blob_client.download_blob = AsyncMock(return_value=stream)
    service = MagicMock()
    service.get_blob_client.return_value = blob_client
    service.__aenter__ = AsyncMock(return_value=service)
    service.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "src.storage.blob.BlobServiceClient.from_connection_string",
        return_value=service,
    ):
        content = await blob.download_file("logos", "key.png")

    assert content == b"file-content"


async def test_download_file_encodes_non_bytes_content() -> None:
    blob_client = MagicMock()
    stream = MagicMock()
    stream.readall = AsyncMock(return_value="text-content")
    blob_client.download_blob = AsyncMock(return_value=stream)
    service = MagicMock()
    service.get_blob_client.return_value = blob_client
    service.__aenter__ = AsyncMock(return_value=service)
    service.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "src.storage.blob.BlobServiceClient.from_connection_string",
        return_value=service,
    ):
        content = await blob.download_file("logos", "key.png")

    assert content == b"text-content"


async def test_delete_file_deletes_blob() -> None:
    blob_client = MagicMock()
    blob_client.delete_blob = AsyncMock()
    service = MagicMock()
    service.get_blob_client.return_value = blob_client
    service.__aenter__ = AsyncMock(return_value=service)
    service.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "src.storage.blob.BlobServiceClient.from_connection_string",
        return_value=service,
    ):
        await blob.delete_file("logos", "key.png")

    blob_client.delete_blob.assert_awaited_once()
