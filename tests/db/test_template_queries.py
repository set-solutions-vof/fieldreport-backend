from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.db import template_queries
from src.models.templates.domain import TemplateSection, TemplateStructure
from src.models.templates.pipeline import TemplateAnalysisFile
from src.models.templates.records import (
    ActiveCompanyTemplateRecord,
    TemplateAnalysisJobRecord,
)


def build_connection(
    company_row: dict[str, object] | None = None,
    job_row: dict[str, object] | None = None,
    rows: list[dict[str, object]] | None = None,
) -> SimpleNamespace:
    row_list = rows or []
    return SimpleNamespace(
        company_row=company_row,
        job_row=job_row,
        rows=row_list,
        fetchrow=AsyncMock(side_effect=[company_row, job_row]),
        fetch=AsyncMock(return_value=row_list),
        execute=AsyncMock(),
        close=AsyncMock(),
    )


async def test_fetch_template_configuration_context_returns_state_context() -> None:
    company_row = {"current_template_id": uuid4(), "structure": '{"sections": []}'}
    created_at = datetime.now(UTC)
    job_row = {
        "id": uuid4(),
        "company_id": uuid4(),
        "status": "pending_review",
        "source_reports_count": 3,
        "structure": (
            '{"sections": [{"id": "summary", "label": "Summary", "render_type": "text_block"}]}'
        ),
        "failure_message": None,
        "created_at": created_at,
    }
    connection = build_connection(company_row, job_row)

    with patch(
        "src.db.template_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        (
            result_active_template,
            result_job_row,
        ) = await template_queries.fetch_template_configuration_context(str(uuid4()))

    assert result_active_template == ActiveCompanyTemplateRecord(
        current_template_id=company_row["current_template_id"],
        structure=TemplateStructure(sections=[]),
    )
    assert result_job_row == TemplateAnalysisJobRecord(
        id=job_row["id"],
        company_id=job_row["company_id"],
        status="pending_review",
        source_reports_count=3,
        structure=TemplateStructure(
            sections=[
                TemplateSection(id="summary", label="Summary", render_type="text_block"),
            ]
        ),
        created_at=created_at,
    )
    assert connection.fetchrow.await_count == 2
    connection.close.assert_awaited_once()


async def test_fetch_active_company_template_returns_company_template() -> None:
    company_row = {"current_template_id": uuid4(), "structure": '{"sections": []}'}
    connection = build_connection()
    connection.fetchrow = AsyncMock(return_value=company_row)

    with patch(
        "src.db.template_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result = await template_queries.fetch_active_company_template(str(uuid4()))

    assert result == ActiveCompanyTemplateRecord(
        current_template_id=company_row["current_template_id"],
        structure=TemplateStructure(sections=[]),
    )
    connection.close.assert_awaited_once()


async def test_replace_template_analysis_job_replaces_existing_company_jobs_and_stores_files() -> (
    None
):
    connection = build_connection()
    stored_files = [
        TemplateAnalysisFile(original_file_name="one.pdf", stored_file_path="/tmp/one.pdf"),
        TemplateAnalysisFile(original_file_name="two.pdf", stored_file_path="/tmp/two.pdf"),
    ]

    with patch(
        "src.db.template_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        await template_queries.replace_template_analysis_job(
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
        {"original_file_name": "one.pdf", "stored_file_path": "/tmp/one.pdf"},
        {"original_file_name": "two.pdf", "stored_file_path": "/tmp/two.pdf"},
    ]
    connection = build_connection(rows=rows)

    with patch(
        "src.db.template_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result = await template_queries.get_template_analysis_job_files(str(uuid4()))

    assert result == [
        TemplateAnalysisFile(original_file_name="one.pdf", stored_file_path="/tmp/one.pdf"),
        TemplateAnalysisFile(original_file_name="two.pdf", stored_file_path="/tmp/two.pdf"),
    ]
    connection.close.assert_awaited_once()


async def test_fetch_template_structure_returns_stored_structure() -> None:
    row = {
        "structure": (
            '{"sections": [{"id": "conclusie", "label": "Conclusie", "render_type": "text_block"}]}'
        )
    }
    connection = build_connection()
    connection.fetchrow = AsyncMock(return_value=row)

    with patch(
        "src.db.template_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        structure = await template_queries.fetch_template_structure("template-id")

    assert structure.sections[0].id == "conclusie"
    connection.fetchrow.assert_awaited_once()
    connection.close.assert_awaited_once()


async def test_get_template_analysis_job_returns_company_scoped_job() -> None:
    created_at = datetime.now(UTC)
    job_row = {
        "id": uuid4(),
        "company_id": uuid4(),
        "status": "queued",
        "source_reports_count": 2,
        "structure": '{"sections": []}',
        "failure_message": None,
        "created_at": created_at,
    }
    connection = build_connection(job_row=job_row)
    connection.fetchrow = AsyncMock(return_value=job_row)

    with patch(
        "src.db.template_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result = await template_queries.get_template_analysis_job(str(uuid4()), str(uuid4()))

    assert result == TemplateAnalysisJobRecord(
        id=job_row["id"],
        company_id=job_row["company_id"],
        status="queued",
        source_reports_count=2,
        structure=TemplateStructure(sections=[]),
        created_at=created_at,
    )
    connection.close.assert_awaited_once()


async def test_get_template_analysis_job_returns_none_when_missing_job() -> None:
    connection = build_connection()
    connection.fetchrow = AsyncMock(return_value=None)

    with patch(
        "src.db.template_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result = await template_queries.get_template_analysis_job(str(uuid4()), str(uuid4()))

    assert result is None
    connection.close.assert_awaited_once()


async def test_fetch_latest_template_analysis_job_returns_latest_company_job() -> None:
    created_at = datetime.now(UTC)
    job_row = {
        "id": uuid4(),
        "company_id": uuid4(),
        "status": "pending_review",
        "source_reports_count": 4,
        "structure": '{"sections": []}',
        "failure_message": None,
        "created_at": created_at,
    }
    connection = build_connection(rows=[job_row])

    with patch(
        "src.db.template_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result = await template_queries.fetch_latest_template_analysis_job(str(uuid4()))

    assert result == TemplateAnalysisJobRecord(
        id=job_row["id"],
        company_id=job_row["company_id"],
        status="pending_review",
        source_reports_count=4,
        structure=TemplateStructure(sections=[]),
        created_at=created_at,
    )
    connection.close.assert_awaited_once()


async def test_fetch_template_configuration_context_handles_null_job_structure() -> None:
    company_row = {"current_template_id": uuid4(), "structure": '{"sections": []}'}
    created_at = datetime.now(UTC)
    job_row = {
        "id": uuid4(),
        "company_id": uuid4(),
        "status": "pending_review",
        "source_reports_count": 2,
        "structure": None,
        "failure_message": None,
        "created_at": created_at,
    }
    connection = build_connection(company_row, job_row)

    with patch(
        "src.db.template_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        (
            result_active_template,
            result_job_row,
        ) = await template_queries.fetch_template_configuration_context(str(uuid4()))

    assert result_active_template == ActiveCompanyTemplateRecord(
        current_template_id=company_row["current_template_id"],
        structure=TemplateStructure(sections=[]),
    )
    assert result_job_row == TemplateAnalysisJobRecord(
        id=job_row["id"],
        company_id=job_row["company_id"],
        status="pending_review",
        source_reports_count=2,
        structure=TemplateStructure(sections=[]),
        created_at=created_at,
    )


async def test_update_template_analysis_job_updates_status_structure_and_failure_message() -> None:
    connection = build_connection()

    with patch(
        "src.db.template_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        await template_queries.update_template_analysis_job(
            str(uuid4()),
            "failed",
            TemplateStructure(sections=[]),
            failure_message="model error",
        )

    assert "UPDATE template_analysis_jobs" in connection.execute.await_args.args[0]
    connection.close.assert_awaited_once()


async def test_delete_template_analysis_job_deletes_company_scoped_job() -> None:
    connection = build_connection()
    job_id = str(uuid4())
    company_id = str(uuid4())

    with patch(
        "src.db.template_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        await template_queries.delete_template_analysis_job(job_id, company_id)

    query = connection.execute.await_args.args[0]
    assert "DELETE FROM template_analysis_jobs" in query
    assert "AND company_id = $2::uuid" in query
    assert connection.execute.await_args.args[1:] == (job_id, company_id)
    connection.close.assert_awaited_once()


async def test_claim_next_template_analysis_job_returns_none_when_no_job_exists() -> None:
    connection = build_connection()
    connection.fetchrow = AsyncMock(return_value=None)

    with patch(
        "src.db.template_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result = await template_queries.claim_next_template_analysis_job()

    assert result is None
    connection.close.assert_awaited_once()


async def test_claim_next_template_analysis_job_returns_processing_job() -> None:
    row = {
        "id": uuid4(),
        "company_id": uuid4(),
        "status": "processing",
        "source_reports_count": 2,
        "structure": None,
        "failure_message": None,
        "created_at": datetime.now(UTC),
    }
    connection = build_connection()
    connection.fetchrow = AsyncMock(return_value=row)

    with patch(
        "src.db.template_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        result = await template_queries.claim_next_template_analysis_job()

    assert result is not None
    assert result.id == row["id"]
    connection.close.assert_awaited_once()


async def test_create_template_inserts_template_structure() -> None:
    connection = build_connection()

    with patch(
        "src.db.template_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        await template_queries.create_template(
            str(uuid4()), str(uuid4()), TemplateStructure(sections=[])
        )

    assert "INSERT INTO templates" in connection.execute.await_args.args[0]
    connection.close.assert_awaited_once()


async def test_set_active_template_updates_company_current_template_id() -> None:
    connection = build_connection()

    with patch(
        "src.db.template_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        await template_queries.set_active_template(str(uuid4()), str(uuid4()))

    assert "UPDATE company" in connection.execute.await_args.args[0]
    connection.close.assert_awaited_once()
