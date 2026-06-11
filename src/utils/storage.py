from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from src.storage import blob
from src.utils.images import normalize_to_jpeg


async def upload_files(container: str, prefix: str, files: list[UploadFile]) -> list[str]:
    keys = []
    for file in files:
        key = f"{prefix}/{uuid4()}{Path(file.filename or '').suffix}"
        await blob.upload_form_file(container, key, file)
        keys.append(key)
    return keys


async def upload_images(container: str, prefix: str, files: list[UploadFile]) -> list[str]:
    keys = []
    for file in files:
        data = await file.read()
        content_type = file.content_type or ""
        data, content_type = normalize_to_jpeg(data, content_type)
        suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(
            content_type, Path(file.filename or "").suffix
        )
        key = f"{prefix}/{uuid4()}{suffix}"
        await blob.upload_file(container, key, data, content_type)
        keys.append(key)
    return keys
