from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.db import template_repository
from src.models.templates.configuration import StoredTemplateStructure, TemplateSection
from src.models.templates.pipeline import TemplateAnalysisFile
from src.models.templates.records import CompanyTemplateRecord, TemplateAnalysisJobRecord
from src.models.templates.state import TemplateCompanyState


class FakeConnection:
    def __init__(self, company_row=None, job_row=None, rows=None):
        self.company_row = company_row
        self.job_row = job_row
        self.rows = rows or []
        self.fetchrow = AsyncMock(side_effect=[company_row, job_row])
        self.fetch = AsyncMock(return_value=self.rows)
        self.execute = AsyncMock()
        self.close = AsyncMock()


async def test_fetch_company_template_context_returns_company_and_latest_job() -> None:
    company_row = {"template_id": uuid4(), "structure": '{"sections": []}'}
    created_at = datetime.now(UTC)
    job_row = {
        "id": uuid4(),
        "company_id": uuid4(),
        "template_id": None,
        "status": "pending_review",
        "reports_count": 3,
        "structure": (
            '{"sections": [{"id": "summary", "label": "Summary", "type": "text_block"}]}'
        ),
        "error_message": None,
        "created_at": created_at,
    }
    connection = FakeConnection(company_row, job_row)

    with patch(
        "src.db.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result_company_row, result_job_row = await template_repository.fetch_company_template_context(
            str(uuid4())
        )

    assert result_company_row == CompanyTemplateRecord(
        template_id=company_row["template_id"],
        structure=StoredTemplateStructure(sections=[]),
    )
    assert result_job_row == TemplateAnalysisJobRecord(
        id=job_row["id"],
        company_id=job_row["company_id"],
        template_id=None,
        status="pending_review",
        reports_count=3,
        structure=StoredTemplateStructure(
            sections=[
                TemplateSection(id="summary", label="Summary", type="text_block"),
            ]
        ),
        error_message=None,
        created_at=created_at,
    )
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
    created_at = datetime.now(UTC)
    job_row = {
        "id": uuid4(),
        "company_id": uuid4(),
        "template_id": None,
        "status": "queued",
        "reports_count": 2,
        "structure": '{"sections": []}',
        "error_message": None,
        "created_at": created_at,
    }
    connection = FakeConnection(job_row=job_row)
    connection.fetchrow = AsyncMock(return_value=job_row)

    with patch(
        "src.db.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result = await template_repository.get_template_analysis_job(str(uuid4()), str(uuid4()))

    assert result == TemplateAnalysisJobRecord(
        id=job_row["id"],
        company_id=job_row["company_id"],
        template_id=None,
        status="queued",
        reports_count=2,
        structure=StoredTemplateStructure(sections=[]),
        error_message=None,
        created_at=created_at,
    )
    connection.close.assert_awaited_once()


async def test_get_template_analysis_job_returns_none_when_missing_job() -> None:
    connection = FakeConnection()
    connection.fetchrow = AsyncMock(return_value=None)

    with patch(
        "src.db.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result = await template_repository.get_template_analysis_job(str(uuid4()), str(uuid4()))

    assert result is None
    connection.close.assert_awaited_once()


async def test_get_template_company_state_resolves_pending_review_job() -> None:
    company_row = {"template_id": None, "structure": None}
    job_row = {
        "id": uuid4(),
        "company_id": uuid4(),
        "template_id": None,
        "status": "pending_review",
        "reports_count": 3,
        "structure": (
            '{"sections": [{"id": "summary", "label": "Summary", "type": "text_block"}]}'
        ),
        "error_message": None,
        "created_at": datetime.now(UTC),
    }
    connection = FakeConnection(company_row, job_row)

    with patch(
        "src.db.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result = await template_repository.get_template_company_state(str(uuid4()))

    assert result == TemplateCompanyState(
        view_status="pending_review",
        structure=StoredTemplateStructure(
            sections=[TemplateSection(id="summary", label="Summary", type="text_block")]
        ),
        job_id=job_row["id"],
        reports_count=3,
    )


async def test_fetch_company_template_context_handles_pre_decoded_and_null_structure() -> None:
    company_row = {"template_id": uuid4(), "structure": {"sections": []}}
    created_at = datetime.now(UTC)
    job_row = {
        "id": uuid4(),
        "company_id": uuid4(),
        "template_id": None,
        "status": "pending_review",
        "reports_count": 2,
        "structure": None,
        "error_message": None,
        "created_at": created_at,
    }
    connection = FakeConnection(company_row, job_row)

    with patch(
        "src.db.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result_company_row, result_job_row = await template_repository.fetch_company_template_context(
            str(uuid4())
        )

    assert result_company_row == CompanyTemplateRecord(
        template_id=company_row["template_id"],
        structure=StoredTemplateStructure(sections=[]),
    )
    assert result_job_row == TemplateAnalysisJobRecord(
        id=job_row["id"],
        company_id=job_row["company_id"],
        template_id=None,
        status="pending_review",
        reports_count=2,
        structure=None,
        error_message=None,
        created_at=created_at,
    )


async def test_update_template_analysis_job_updates_status_structure_and_error_message() -> None:
    connection = FakeConnection()

    with patch(
        "src.db.template_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        await template_repository.update_template_analysis_job(
            str(uuid4()),
            "failed",
            StoredTemplateStructure(sections=[]),
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
        await template_repository.create_template(
            str(uuid4()), str(uuid4()), StoredTemplateStructure(sections=[])
        )

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
