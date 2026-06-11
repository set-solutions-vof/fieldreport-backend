from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from src.db.inspection import queries
from src.db.schema.tables import (
    inspection_audio_files,
    inspection_photo_files,
    inspections,
    reports,
)
from src.models.reports.metadata import ReportMetadata
from tests.db.sqlalchemy_fakes import build_connection


def mock_pool(connection):
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return patch("src.db.inspection.queries.get_database", return_value=pool)


async def test_insert_inspection_executes_insert() -> None:
    connection = build_connection()

    await queries.insert_inspection(
        connection,
        "inspection-id",
        "company-id",
        "inspector-id",
        "template-id",
        ReportMetadata.model_validate({"type_onderzoek": "Investigation"}),
        "Context",
        date(2026, 5, 25),
    )

    connection.execute.assert_awaited_once()
    statement = connection.execute.await_args.args[0]
    assert statement.table is inspections


async def test_insert_inspection_audio_file_executes_insert() -> None:
    connection = build_connection()

    await queries.insert_inspection_audio_file(
        connection,
        "inspection-id",
        "/tmp/audio.m4a",
        "audio.m4a",
    )

    connection.execute.assert_awaited_once()
    statement = connection.execute.await_args.args[0]
    assert statement.table is inspection_audio_files


async def test_insert_inspection_photo_file_executes_insert() -> None:
    connection = build_connection()

    await queries.insert_inspection_photo_file(
        connection,
        "inspection-id",
        "/tmp/photo.jpg",
        "photo.jpg",
    )

    connection.execute.assert_awaited_once()
    statement = connection.execute.await_args.args[0]
    assert statement.table is inspection_photo_files


async def test_fetch_inspection_audio_files_returns_rows() -> None:
    from src.models.reports.pipeline import InspectionMediaFile

    rows = [{"storage_key": "/tmp/audio.m4a", "original_file_name": "audio.m4a"}]
    connection = build_connection(rows=rows)

    with mock_pool(connection):
        result = await queries.fetch_inspection_audio_files("inspection-id")

    assert result == [
        InspectionMediaFile(storage_key="/tmp/audio.m4a", original_file_name="audio.m4a")
    ]
    connection.execute.assert_awaited_once()


async def test_inspection_photo_belongs_to_company_returns_true_when_found() -> None:
    connection = build_connection(row=(1,))

    with mock_pool(connection):
        result = await queries.inspection_photo_belongs_to_company(
            "company-id",
            "company-id/inspection-id/photos/photo.jpg",
        )

    assert result is True
    connection.execute.assert_awaited_once()


async def test_inspection_photo_belongs_to_company_returns_false_when_missing() -> None:
    connection = build_connection()

    with mock_pool(connection):
        result = await queries.inspection_photo_belongs_to_company(
            "company-id",
            "other-company/inspection-id/photos/photo.jpg",
        )

    assert result is False
    connection.execute.assert_awaited_once()


async def test_fetch_inspection_photo_files_returns_rows() -> None:
    from src.models.reports.pipeline import InspectionMediaFile

    rows = [{"storage_key": "/tmp/photo.jpg", "original_file_name": "photo.jpg"}]
    connection = build_connection(rows=rows)

    with mock_pool(connection):
        result = await queries.fetch_inspection_photo_files("inspection-id")

    assert result == [
        InspectionMediaFile(storage_key="/tmp/photo.jpg", original_file_name="photo.jpg")
    ]
    connection.execute.assert_awaited_once()


async def test_insert_report_executes_insert() -> None:
    connection = build_connection()

    await queries.insert_report(
        connection,
        "report-id",
        "inspection-id",
        "company-id",
        "template-id",
    )

    connection.execute.assert_awaited_once()
    statement = connection.execute.await_args.args[0]
    assert statement.table is reports
