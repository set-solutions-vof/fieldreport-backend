from azure.storage.blob import ContentSettings
from azure.storage.blob.aio import BlobServiceClient

from src.config import settings

_service_client: BlobServiceClient | None = None


async def upload_file(container: str, key: str, data: bytes, content_type: str) -> str:
    blob_client = _service_client_instance().get_blob_client(container=container, blob=key)
    await blob_client.upload_blob(
        data,
        blob_type="BlockBlob",
        content_settings=ContentSettings(content_type=content_type),
        overwrite=True,
    )
    return blob_client.url


async def download_file(container: str, key: str) -> tuple[bytes, str]:
    blob_client = _service_client_instance().get_blob_client(container=container, blob=key)
    properties = await blob_client.get_blob_properties()
    stream = await blob_client.download_blob()
    content = await stream.readall()
    content_type = properties.content_settings.content_type or "application/octet-stream"
    return content if isinstance(content, bytes) else content.encode(), content_type


async def ensure_containers() -> None:
    service = _service_client_instance()
    for name in ["inspections", "templates"]:
        container = service.get_container_client(name)
        if not await container.exists():
            await container.create_container()

    logos = service.get_container_client("logos")
    if not await logos.exists():
        await logos.create_container(public_access="blob")


async def close_service_client() -> None:
    global _service_client

    if _service_client is not None:
        await _service_client.close()
        _service_client = None


def _service_client_instance() -> BlobServiceClient:
    global _service_client

    if _service_client is None:
        _service_client = BlobServiceClient.from_connection_string(
            settings.azure_storage_connection_string
        )

    return _service_client
