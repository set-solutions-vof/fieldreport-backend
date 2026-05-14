from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.db import template_repository
from src.models.templates.template_analysis import TemplateAnalysisFile


class FakeConnection:
    def __init__(self, company_row=None, job_row=None, rows=None):
        self.company_row = company_row
        self.job_row = job_row
        self.rows = rows or []
        self.fetchrow = AsyncMock(side_effect=[company_row, job_row])
        self.fetch = AsyncMock(return_value=self.rows)
        self.execute = AsyncMock()
        self.close = AsyncMock()


async def test_get_company_template_context_returns_company_and_latest_job() -> None:
    company_row = {"active_template_id": uuid4(), "active_structure": {"sections": []}}
    job_row = {
        "id": uuid4(),
        "status": "pending_review",
        "reports_count": 3,
        "structure": {},
        "error_message": None,
    }
    connection = FakeConnection(company_row, job_row)

    with patch(
        "src.db.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result_company_row, result_job_row = await template_repository.get_company_template_context(
            str(uuid4())
        )

    assert result_company_row == company_row
    assert result_job_row == job_row
    assert connection.fetchrow.await_count == 2
    connection.close.assert_awaited_once()


async def test_replace_template_analysis_job_replaces_existing_company_jobs_and_stores_files() -> (
    None
):
    connection = FakeConnection()
    stored_files = [
        TemplateAnalysisFile(file_name="one.pdf", storage_path="/tmp/one.pdf"),
        TemplateAnalysisFile(file_name="two.pdf", storage_path="/tmp/two.pdf"),
    ]

    with patch(
        "src.db.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        await template_repository.replace_template_analysis_job(
            str(uuid4()),
            str(uuid4()),
            stored_files,
        )

    assert connection.execute.await_count == 4
    assert "DELETE FROM template_analysis_jobs" in connection.execute.await_args_list[0].args[0]
    assert "INSERT INTO template_analysis_jobs" in connection.execute.await_args_list[1].args[0]
    assert (
        "INSERT INTO template_analysis_job_files" in connection.execute.await_args_list[2].args[0]
    )
    connection.close.assert_awaited_once()


async def test_get_template_analysis_job_files_returns_stored_files() -> None:
    rows = [
        {"file_name": "one.pdf", "storage_path": "/tmp/one.pdf"},
        {"file_name": "two.pdf", "storage_path": "/tmp/two.pdf"},
    ]
    connection = FakeConnection(rows=rows)

    with patch(
        "src.db.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result = await template_repository.get_template_analysis_job_files(str(uuid4()))

    assert result == [
        TemplateAnalysisFile(file_name="one.pdf", storage_path="/tmp/one.pdf"),
        TemplateAnalysisFile(file_name="two.pdf", storage_path="/tmp/two.pdf"),
    ]
    connection.close.assert_awaited_once()


async def test_get_template_analysis_job_returns_company_scoped_job() -> None:
    job_row = {"id": uuid4(), "status": "queued", "reports_count": 2, "error_message": None}
    connection = FakeConnection(job_row=job_row)
    connection.fetchrow = AsyncMock(return_value=job_row)

    with patch(
        "src.db.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result = await template_repository.get_template_analysis_job(str(uuid4()), str(uuid4()))

    assert result == job_row
    connection.close.assert_awaited_once()


async def test_update_template_analysis_job_updates_status_structure_and_error_message() -> None:
    connection = FakeConnection()

    with patch(
        "src.db.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        await template_repository.update_template_analysis_job(
            str(uuid4()),
            "failed",
            {"sections": []},
            error_message="model error",
        )

    assert "UPDATE template_analysis_jobs" in connection.execute.await_args.args[0]
    connection.close.assert_awaited_once()


async def test_claim_next_template_analysis_job_returns_none_when_no_job_exists() -> None:
    connection = FakeConnection()
    connection.fetchrow = AsyncMock(return_value=None)

    with patch(
        "src.db.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result = await template_repository.claim_next_template_analysis_job()

    assert result is None
    connection.close.assert_awaited_once()


async def test_claim_next_template_analysis_job_returns_processing_job() -> None:
    row = {
        "id": uuid4(),
        "company_id": uuid4(),
        "template_id": uuid4(),
        "status": "processing",
        "reports_count": 2,
        "structure": None,
        "error_message": None,
    }
    connection = FakeConnection()
    connection.fetchrow = AsyncMock(return_value=row)

    with patch(
        "src.db.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result = await template_repository.claim_next_template_analysis_job()

    assert result is not None
    assert result.id == str(row["id"])
    assert result.template_id == str(row["template_id"])
    connection.close.assert_awaited_once()


async def test_create_template_inserts_template_structure() -> None:
    connection = FakeConnection()

    with patch(
        "src.db.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        await template_repository.create_template(str(uuid4()), str(uuid4()), {"sections": []})

    assert "INSERT INTO templates" in connection.execute.await_args.args[0]
    connection.close.assert_awaited_once()


async def test_set_active_template_updates_company_active_template_id() -> None:
    connection = FakeConnection()

    with patch(
        "src.db.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        await template_repository.set_active_template(str(uuid4()), str(uuid4()))

    assert "UPDATE company" in connection.execute.await_args.args[0]
    connection.close.assert_awaited_once()
