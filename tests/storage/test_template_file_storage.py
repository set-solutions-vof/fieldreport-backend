from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from starlette.datastructures import UploadFile

from src.storage import template_file_storage


async def test_store_template_analysis_files_persists_uploaded_files(tmp_path: Path) -> None:
    files = [
        UploadFile(filename="one.pdf", file=BytesIO(b"one")),
        UploadFile(filename="two.pdf", file=BytesIO(b"two")),
    ]

    with patch.object(
        template_file_storage.settings,
        "template_analysis_storage_path",
        str(tmp_path),
    ):
        stored_files = await template_file_storage.store_template_analysis_files(
            "company-1",
            "job-1",
            files,
        )

    assert [stored_file.file_name for stored_file in stored_files] == ["one.pdf", "two.pdf"]
    assert all(Path(stored_file.storage_path).exists() for stored_file in stored_files)
    assert await files[0].read() == b"one"


def test_get_template_analysis_storage_directory_returns_resolved_path(tmp_path: Path) -> None:
    with patch.object(
        template_file_storage.settings,
        "template_analysis_storage_path",
        str(tmp_path),
    ):
        result = template_file_storage.get_template_analysis_storage_directory()

    assert result == tmp_path.resolve()


def test_load_template_analysis_file_reads_file_content(tmp_path: Path) -> None:
    file_path = tmp_path / "report.pdf"
    file_path.write_bytes(b"pdf-content")

    assert template_file_storage.load_template_analysis_file(str(file_path)) == b"pdf-content"
