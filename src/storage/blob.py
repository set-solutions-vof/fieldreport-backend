from azure.storage.blob import ContentSettings
from azure.storage.blob.aio import BlobServiceClient
from fastapi import UploadFile

from src.config import settings


async def upload_form_file(container: str, key: str, file: UploadFile) -> str:
    data = await file.read()
    return await upload_file(container, key, data, file.content_type or "application/octet-stream")


async def upload_file(container: str, key: str, data: bytes, content_type: str) -> str:
    async with BlobServiceClient.from_connection_string(
        settings.azure_storage_connection_string
    ) as service:
        blob = service.get_blob_client(container=container, blob=key)
        await blob.upload_blob(
            data,
            blob_type="BlockBlob",
            content_settings=ContentSettings(content_type=content_type),
            overwrite=True,
        )
        return blob.url


async def download_file(container: str, key: str) -> bytes:
    async with BlobServiceClient.from_connection_string(
        settings.azure_storage_connection_string
    ) as service:
        blob = service.get_blob_client(container=container, blob=key)
        stream = await blob.download_blob()
        content = await stream.readall()
        return content if isinstance(content, bytes) else content.encode()


async def delete_file(container: str, key: str) -> None:
    async with BlobServiceClient.from_connection_string(
        settings.azure_storage_connection_string
    ) as service:
        blob = service.get_blob_client(container=container, blob=key)
        await blob.delete_blob()
