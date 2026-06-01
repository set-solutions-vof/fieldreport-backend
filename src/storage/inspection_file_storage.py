from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from src.config import settings


def get_inspection_storage_directory() -> Path:
    return Path(settings.inspection_stored_file_path).resolve()


async def store_inspection_files(
    company_id: str,
    inspection_id: str,
    audio_files: list[UploadFile],
    photo_files: list[UploadFile],
) -> tuple[list[str], list[str]]:
    inspection_directory = get_inspection_storage_directory() / company_id / inspection_id
    audio_directory = inspection_directory / "audio"
    photo_directory = inspection_directory / "photos"
    audio_directory.mkdir(parents=True, exist_ok=True)
    photo_directory.mkdir(parents=True, exist_ok=True)

    audio_storage_keys = await store_files(audio_directory, audio_files)
    photo_storage_keys = await store_files(photo_directory, photo_files)

    return audio_storage_keys, photo_storage_keys


async def store_files(directory: Path, files: list[UploadFile]) -> list[str]:
    storage_keys: list[str] = []

    for file in files:
        original_file_name = file.filename or str(uuid4())
        file_extension = Path(original_file_name).suffix
        stored_file_path = directory / f"{uuid4()}{file_extension}"
        file_content = await file.read()

        stored_file_path.write_bytes(file_content)
        await file.seek(0)

        storage_keys.append(str(stored_file_path))

    return storage_keys


def load_inspection_file(storage_key: str) -> bytes:
    return Path(storage_key).read_bytes()
