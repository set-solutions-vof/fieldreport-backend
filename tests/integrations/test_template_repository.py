from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.integrations import template_repository


class FakeConnection:
    def __init__(self, company_row=None, job_row=None):
        self.company_row = company_row
        self.job_row = job_row
        self.fetchrow = AsyncMock(side_effect=[company_row, job_row])
        self.execute = AsyncMock()
        self.close = AsyncMock()


async def test_get_company_template_context_returns_company_and_latest_job() -> None:
    company_row = {"active_template_id": uuid4(), "active_structure": {"sections": []}}
    job_row = {"id": uuid4(), "status": "pending_review", "reports_count": 3, "structure": {}}
    connection = FakeConnection(company_row, job_row)

    with patch(
        "src.integrations.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result_company_row, result_job_row = await template_repository.get_company_template_context(
            str(uuid4())
        )

    assert result_company_row == company_row
    assert result_job_row == job_row
    assert connection.fetchrow.await_count == 2
    connection.close.assert_awaited_once()


async def test_replace_template_analysis_job_replaces_existing_company_jobs() -> None:
    connection = FakeConnection()

    with patch(
        "src.integrations.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        await template_repository.replace_template_analysis_job(str(uuid4()), str(uuid4()), 3)

    assert connection.execute.await_count == 2
    assert "DELETE FROM template_analysis_jobs" in connection.execute.await_args_list[0].args[0]
    assert "INSERT INTO template_analysis_jobs" in connection.execute.await_args_list[1].args[0]
    connection.close.assert_awaited_once()


async def test_get_template_analysis_job_returns_company_scoped_job() -> None:
    job_row = {"id": uuid4(), "status": "extracting", "reports_count": 2}
    connection = FakeConnection(job_row=job_row)
    connection.fetchrow = AsyncMock(return_value=job_row)

    with patch(
        "src.integrations.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result = await template_repository.get_template_analysis_job(str(uuid4()), str(uuid4()))

    assert result == job_row
    connection.fetchrow.assert_awaited_once()
    connection.close.assert_awaited_once()


async def test_update_template_analysis_job_updates_status_structure_and_template_id() -> None:
    connection = FakeConnection()

    with patch(
        "src.integrations.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        await template_repository.update_template_analysis_job(
            str(uuid4()),
            "active",
            {"sections": []},
            str(uuid4()),
        )

    assert connection.execute.await_count == 1
    assert "UPDATE template_analysis_jobs" in connection.execute.await_args.args[0]
    connection.close.assert_awaited_once()


async def test_create_template_inserts_template_structure() -> None:
    connection = FakeConnection()

    with patch(
        "src.integrations.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        await template_repository.create_template(str(uuid4()), str(uuid4()), {"sections": []})

    assert connection.execute.await_count == 1
    assert "INSERT INTO templates" in connection.execute.await_args.args[0]
    connection.close.assert_awaited_once()


async def test_set_active_template_updates_company_active_template_id() -> None:
    connection = FakeConnection()

    with patch(
        "src.integrations.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        await template_repository.set_active_template(str(uuid4()), str(uuid4()))

    assert connection.execute.await_count == 1
    assert "UPDATE company" in connection.execute.await_args.args[0]
    connection.close.assert_awaited_once()
