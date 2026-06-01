from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from starlette.datastructures import UploadFile

from src.storage import inspection_file_storage


async def test_store_inspection_files_persists_audio_and_photos(tmp_path: Path) -> None:
    audio_files = [UploadFile(filename="audio.m4a", file=BytesIO(b"audio"))]
    photo_files = [UploadFile(filename="photo.jpg", file=BytesIO(b"photo"))]

    with patch.object(
        inspection_file_storage.settings, "inspection_stored_file_path", str(tmp_path)
    ):
        audio_keys, photo_keys = await inspection_file_storage.store_inspection_files(
            "company-1",
            "inspection-1",
            audio_files,
            photo_files,
        )

    assert len(audio_keys) == 1
    assert len(photo_keys) == 1
    assert Path(audio_keys[0]).read_bytes() == b"audio"
    assert Path(photo_keys[0]).read_bytes() == b"photo"
    assert await audio_files[0].read() == b"audio"


def test_get_inspection_storage_directory_returns_resolved_path(tmp_path: Path) -> None:
    with patch.object(
        inspection_file_storage.settings, "inspection_stored_file_path", str(tmp_path)
    ):
        result = inspection_file_storage.get_inspection_storage_directory()

    assert result == tmp_path.resolve()


def test_load_inspection_file_reads_file_content(tmp_path: Path) -> None:
    file_path = tmp_path / "audio.m4a"
    file_path.write_bytes(b"audio-content")

    assert inspection_file_storage.load_inspection_file(str(file_path)) == b"audio-content"
