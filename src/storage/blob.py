from azure.storage.blob import ContentSettings
from azure.storage.blob.aio import BlobServiceClient
from fastapi import UploadFile

from src.config import settings


async def upload_form_file(container: str, key: str, file: UploadFile) -> str:
    data = await file.read()
    return await upload_file(container, key, data, file.content_type or "application/octet-stream")


async def upload_file(container: str, key: str, data: bytes, content_type: str) -> str:
    async with _service() as service:
        blob_client = service.get_blob_client(container=container, blob=key)
        await blob_client.upload_blob(
            data,
            blob_type="BlockBlob",
            content_settings=ContentSettings(content_type=content_type),
            overwrite=True,
        )
        return blob_client.url


async def download_file(container: str, key: str) -> bytes:
    async with _service() as service:
        blob_client = service.get_blob_client(container=container, blob=key)
        stream = await blob_client.download_blob()
        content = await stream.readall()
        return content if isinstance(content, bytes) else content.encode()


async def delete_file(container: str, key: str) -> None:
    async with _service() as service:
        blob_client = service.get_blob_client(container=container, blob=key)
        await blob_client.delete_blob()


async def ensure_containers() -> None:
    async with _service() as service:
        for name in ["inspections", "templates"]:
            container = service.get_container_client(name)
            if not await container.exists():
                await container.create_container()

        logos = service.get_container_client("logos")
        if not await logos.exists():
            await logos.create_container(public_access="blob")


def _service() -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)
