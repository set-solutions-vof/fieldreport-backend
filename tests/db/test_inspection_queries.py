from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.db import inspection_queries


def build_connection(rows: list[dict[str, object]] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        rows=rows,
        execute=AsyncMock(),
        fetch=AsyncMock(return_value=rows),
        close=AsyncMock(),
    )


async def test_insert_inspection_executes_insert() -> None:
    connection = build_connection()

    with patch("src.db.inspection_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        await inspection_queries.insert_inspection(
            "inspection-id",
            "company-id",
            "inspector-id",
            "template-id",
            "Client",
            "Address",
            "Investigation",
            "Business",
            "Context",
            date(2026, 5, 25),
        )

    connection.execute.assert_awaited_once()
    assert connection.execute.await_args.args[-1] == date(2026, 5, 25)
    connection.close.assert_awaited_once()


async def test_insert_inspection_audio_file_executes_insert() -> None:
    connection = build_connection()

    with patch("src.db.inspection_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        await inspection_queries.insert_inspection_audio_file(
            "inspection-id",
            "/tmp/audio.m4a",
            "audio.m4a",
        )

    connection.execute.assert_awaited_once()
    assert connection.execute.await_args.args[-2:] == ("/tmp/audio.m4a", "audio.m4a")
    connection.close.assert_awaited_once()


async def test_insert_inspection_photo_file_executes_insert() -> None:
    connection = build_connection()

    with patch("src.db.inspection_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        await inspection_queries.insert_inspection_photo_file(
            "inspection-id",
            "/tmp/photo.jpg",
            "photo.jpg",
        )

    connection.execute.assert_awaited_once()
    assert connection.execute.await_args.args[-2:] == ("/tmp/photo.jpg", "photo.jpg")
    connection.close.assert_awaited_once()


async def test_fetch_inspection_audio_files_returns_rows() -> None:
    from src.models.reports.pipeline import InspectionMediaFile

    rows = [{"storage_key": "/tmp/audio.m4a", "original_file_name": "audio.m4a"}]
    connection = build_connection(rows)

    with patch("src.db.inspection_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        result = await inspection_queries.fetch_inspection_audio_files("inspection-id")

    assert result == [
        InspectionMediaFile(storage_key="/tmp/audio.m4a", original_file_name="audio.m4a")
    ]
    connection.fetch.assert_awaited_once()
    connection.close.assert_awaited_once()


async def test_fetch_inspection_photo_files_returns_rows() -> None:
    from src.models.reports.pipeline import InspectionMediaFile

    rows = [{"storage_key": "/tmp/photo.jpg", "original_file_name": "photo.jpg"}]
    connection = build_connection(rows)

    with patch("src.db.inspection_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        result = await inspection_queries.fetch_inspection_photo_files("inspection-id")

    assert result == [
        InspectionMediaFile(storage_key="/tmp/photo.jpg", original_file_name="photo.jpg")
    ]
    connection.fetch.assert_awaited_once()
    connection.close.assert_awaited_once()


async def test_insert_report_executes_insert() -> None:
    connection = build_connection()

    with patch("src.db.inspection_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        await inspection_queries.insert_report(
            "report-id",
            "inspection-id",
            "company-id",
            "template-id",
        )

    connection.execute.assert_awaited_once()
    assert connection.execute.await_args.args[-4:] == (
        "report-id",
        "inspection-id",
        "company-id",
        "template-id",
    )
    connection.close.assert_awaited_once()
