from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.db.schema.tables import (
    company,
    template_analysis_job_files,
    template_analysis_jobs,
    templates,
)
from src.db.template import queries
from src.models.templates.domain import TemplateSection, TemplateStructure
from src.models.templates.pipeline import TemplateAnalysisFile
from src.models.templates.records import (
    ActiveCompanyTemplateRecord,
    TemplateAnalysisJobRecord,
)
from tests.db.sqlalchemy_fakes import (
    FakeResult,
)
from tests.db.sqlalchemy_fakes import (
    build_connection as build_fake_connection,
)


def build_connection(
    company_row: dict[str, object] | None = None,
    job_row: dict[str, object] | None = None,
    rows: list[dict[str, object]] | None = None,
) -> object:
    results = []

    if company_row is not None:
        results.append(FakeResult(row=company_row))

    if job_row is not None:
        results.append(FakeResult(row=job_row))

    if rows is not None:
        results.append(FakeResult(rows=rows))

    return build_fake_connection(
        row=None if results else None,
        rows=None,
        results=results if results else None,
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

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        (
            result_active_template,
            result_job_row,
        ) = await queries.fetch_template_configuration_context(str(uuid4()))

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
    assert connection.execute.await_count == 2


async def test_fetch_active_company_template_returns_company_template() -> None:
    company_row = {"current_template_id": uuid4(), "structure": '{"sections": []}'}
    connection = build_fake_connection(row=company_row)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        result = await queries.fetch_active_company_template(str(uuid4()))

    assert result == ActiveCompanyTemplateRecord(
        current_template_id=company_row["current_template_id"],
        structure=TemplateStructure(sections=[]),
    )
    connection.execute.assert_awaited_once()


async def test_replace_template_analysis_job_replaces_existing_company_jobs_and_stores_files() -> (
    None
):
    connection = build_connection()
    stored_files = [
        TemplateAnalysisFile(original_file_name="one.pdf", stored_file_path="/tmp/one.pdf"),
        TemplateAnalysisFile(original_file_name="two.pdf", stored_file_path="/tmp/two.pdf"),
    ]

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        await queries.replace_template_analysis_job(
            str(uuid4()),
            str(uuid4()),
            stored_files,
        )

    assert connection.execute.await_count == 4
    assert connection.execute.await_args_list[0].args[0].table is template_analysis_jobs
    assert connection.execute.await_args_list[1].args[0].table is template_analysis_jobs
    assert connection.execute.await_args_list[2].args[0].table is template_analysis_job_files


async def test_get_template_analysis_job_files_returns_stored_files() -> None:
    rows = [
        {"original_file_name": "one.pdf", "stored_file_path": "/tmp/one.pdf"},
        {"original_file_name": "two.pdf", "stored_file_path": "/tmp/two.pdf"},
    ]
    connection = build_connection(rows=rows)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        result = await queries.get_template_analysis_job_files(str(uuid4()))

    assert result == [
        TemplateAnalysisFile(original_file_name="one.pdf", stored_file_path="/tmp/one.pdf"),
        TemplateAnalysisFile(original_file_name="two.pdf", stored_file_path="/tmp/two.pdf"),
    ]
    connection.execute.assert_awaited_once()


async def test_fetch_template_structure_returns_stored_structure() -> None:
    row = {
        "structure": (
            '{"sections": [{"id": "conclusie", "label": "Conclusie", "render_type": "text_block"}]}'
        )
    }
    connection = build_fake_connection(row=row)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        structure = await queries.fetch_template_structure("template-id", "company-id")

    assert structure.sections[0].id == "conclusie"
    connection.execute.assert_awaited_once()


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
    connection = build_fake_connection(row=job_row)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        result = await queries.get_template_analysis_job(str(uuid4()), str(uuid4()))

    assert result == TemplateAnalysisJobRecord(
        id=job_row["id"],
        company_id=job_row["company_id"],
        status="queued",
        source_reports_count=2,
        structure=TemplateStructure(sections=[]),
        created_at=created_at,
    )
    connection.execute.assert_awaited_once()


async def test_get_template_analysis_job_returns_none_when_missing_job() -> None:
    connection = build_fake_connection(row=None)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        result = await queries.get_template_analysis_job(str(uuid4()), str(uuid4()))

    assert result is None
    connection.execute.assert_awaited_once()


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
    connection = build_fake_connection(row=job_row)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        result = await queries.fetch_latest_template_analysis_job(str(uuid4()))

    assert result == TemplateAnalysisJobRecord(
        id=job_row["id"],
        company_id=job_row["company_id"],
        status="pending_review",
        source_reports_count=4,
        structure=TemplateStructure(sections=[]),
        created_at=created_at,
    )
    connection.execute.assert_awaited_once()


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

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        (
            result_active_template,
            result_job_row,
        ) = await queries.fetch_template_configuration_context(str(uuid4()))

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
    assert connection.execute.await_count == 2


async def test_update_template_analysis_job_updates_status_structure_and_failure_message() -> None:
    connection = build_connection()

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        await queries.update_template_analysis_job(
            str(uuid4()),
            "failed",
            TemplateStructure(sections=[]),
            failure_message="model error",
        )

    statement = connection.execute.await_args.args[0]
    assert statement.table is template_analysis_jobs


async def test_delete_template_analysis_job_deletes_company_scoped_job() -> None:
    connection = build_connection()
    job_id = str(uuid4())
    company_id = str(uuid4())

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        await queries.delete_template_analysis_job(job_id, company_id)

    query = connection.execute.await_args.args[0]
    assert query.table is template_analysis_jobs


async def test_claim_next_template_analysis_job_returns_none_when_no_job_exists() -> None:
    connection = build_fake_connection(row=None)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        result = await queries.claim_next_template_analysis_job()

    assert result is None
    connection.execute.assert_awaited_once()


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
    connection = build_fake_connection(row=row)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        result = await queries.claim_next_template_analysis_job()

    assert result is not None
    assert result.id == row["id"]
    connection.execute.assert_awaited_once()


async def test_create_template_inserts_template_structure() -> None:
    connection = build_connection()

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        await queries.create_template(str(uuid4()), str(uuid4()), TemplateStructure(sections=[]))

    statement = connection.execute.await_args.args[0]
    assert statement.table is templates


async def test_set_active_template_updates_company_current_template_id() -> None:
    connection = build_connection()

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        await queries.set_active_template(str(uuid4()), str(uuid4()))

    statement = connection.execute.await_args.args[0]
    assert statement.table is company


async def test_fetch_optional_active_company_template_returns_none_without_template() -> None:
    connection = build_connection(
        company_row={"current_template_id": None, "structure": None},
    )

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        result = await queries.fetch_optional_active_company_template(str(uuid4()))

    assert result is None


async def test_fetch_latest_template_analysis_job_raises_when_no_job_exists() -> None:
    connection = build_fake_connection(row=None)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        try:
            await queries.fetch_latest_template_analysis_job(str(uuid4()))
        except IndexError:
            pass
        else:
            raise AssertionError("Expected IndexError")
    connection.execute.assert_awaited_once()


async def test_fetch_optional_latest_template_analysis_job_returns_none_when_missing() -> None:
    connection = build_fake_connection(row=None)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        result = await queries.fetch_optional_latest_template_analysis_job(str(uuid4()))

    assert result is None
    connection.execute.assert_awaited_once()


async def test_fetch_active_company_template_raises_when_missing() -> None:
    connection = build_fake_connection(row=None)
    company_id = str(uuid4())

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        with pytest.raises(RuntimeError):
            await queries.fetch_active_company_template(company_id)
