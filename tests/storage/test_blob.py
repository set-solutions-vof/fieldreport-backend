from unittest.mock import AsyncMock, MagicMock, patch

from src.storage import blob


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
