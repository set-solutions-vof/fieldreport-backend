from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.db.schema.tables import company, templates
from src.db.template import queries
from src.models.templates.domain import TemplateSection, TemplateStructure
from src.models.templates.records import ActiveCompanyTemplateRecord
from tests.db.sqlalchemy_fakes import FakeResult
from tests.db.sqlalchemy_fakes import build_connection as build_fake_connection


def build_connection(
    company_row: dict[str, object] | None = None,
) -> object:
    results = []

    if company_row is not None:
        results.append(FakeResult(row=company_row))

    return build_fake_connection(
        row=None if results else None,
        rows=None,
        results=results if results else None,
    )


async def test_fetch_active_company_template_returns_company_template() -> None:
    created_at = datetime.now(UTC)
    company_row = {
        "current_template_id": uuid4(),
        "structure": '{"sections": []}',
        "created_at": created_at,
        "version": 1,
        "source_reports_count": 0,
    }
    connection = build_fake_connection(row=company_row)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        result = await queries.fetch_active_company_template(str(uuid4()))

    assert result == ActiveCompanyTemplateRecord(
        current_template_id=company_row["current_template_id"],
        structure=TemplateStructure(sections=[]),
        created_at=created_at,
        version=1,
        source_reports_count=0,
    )
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


async def test_create_template_inserts_template_structure() -> None:
    connection = build_connection()

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        await queries.create_template(str(uuid4()), str(uuid4()), TemplateStructure(sections=[]), 4)

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


async def test_fetch_active_company_template_raises_when_missing() -> None:
    connection = build_fake_connection(row=None)
    company_id = str(uuid4())

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.template.queries.get_database", return_value=pool):
        with pytest.raises(RuntimeError):
            await queries.fetch_active_company_template(company_id)
