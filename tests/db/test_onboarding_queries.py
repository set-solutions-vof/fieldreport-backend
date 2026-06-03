from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.db import onboarding_queries
from src.http.v1.response.onboarding import (
    CompanyOnboardingResponse,
    InviteCreatedResponse,
    InviteResponse,
)


def build_connection(
    row: dict[str, object] | None = None,
    rows: list[dict[str, object]] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        fetchrow=AsyncMock(return_value=row),
        fetch=AsyncMock(return_value=rows or []),
        close=AsyncMock(),
    )


async def test_get_company_returns_company_response() -> None:
    company_id = uuid4()
    row = {
        "id": company_id,
        "name": "LEKK BV",
        "logo_url": None,
        "primary_color": "#3B5BDB",
        "onboarding_completed": False,
    }
    connection = build_connection(row)

    with patch(
        "src.db.onboarding_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        company = await onboarding_queries.get_company(str(company_id))

    assert company == CompanyOnboardingResponse(
        id=company_id,
        name="LEKK BV",
        logo_url=None,
        primary_color="#3B5BDB",
        onboarding_completed=False,
    )
    connection.close.assert_awaited_once()


async def test_update_company_returns_updated_company_response() -> None:
    company_id = uuid4()
    row = {
        "id": company_id,
        "name": "LEKK BV",
        "logo_url": "https://cdn.example/logo.png",
        "primary_color": "#3B5BDB",
        "onboarding_completed": True,
    }
    connection = build_connection(row)

    with patch(
        "src.db.onboarding_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        company = await onboarding_queries.update_company(
            str(company_id),
            "https://cdn.example/logo.png",
            "#3B5BDB",
            True,
            True,
            True,
            True,
        )

    assert company.logo_url == "https://cdn.example/logo.png"
    assert company.onboarding_completed is True
    assert connection.fetchrow.await_args.args[1:] == (
        str(company_id),
        True,
        "https://cdn.example/logo.png",
        True,
        "#3B5BDB",
        True,
        True,
    )
    connection.close.assert_awaited_once()


async def test_has_pending_invite_returns_true_for_existing_pending_invite() -> None:
    connection = build_connection({"id": uuid4()})

    with patch(
        "src.db.onboarding_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        has_pending_invite = await onboarding_queries.has_pending_invite(
            str(uuid4()),
            "new.user@lekk.nl",
        )

    assert has_pending_invite is True
    connection.close.assert_awaited_once()


async def test_create_invite_returns_created_invite_response() -> None:
    invite_id = uuid4()
    created_at = datetime.now(UTC)
    expires_at = datetime.now(UTC)
    row = {
        "id": invite_id,
        "email": "new.user@lekk.nl",
        "role": "admin",
        "created_at": created_at,
    }
    connection = build_connection(row)

    with patch(
        "src.db.onboarding_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        invite = await onboarding_queries.create_invite(
            str(uuid4()),
            "new.user@lekk.nl",
            "admin",
            "token",
            expires_at,
        )

    assert invite == InviteCreatedResponse(
        id=invite_id,
        email="new.user@lekk.nl",
        role="admin",
        created_at=created_at,
    )
    connection.close.assert_awaited_once()


async def test_list_invites_returns_company_invites() -> None:
    created_at = datetime.now(UTC)
    expires_at = datetime.now(UTC)
    invite_id = uuid4()
    row = {
        "id": invite_id,
        "email": "new.user@lekk.nl",
        "role": "inspector",
        "is_accepted": False,
        "created_at": created_at,
        "expires_at": expires_at,
    }
    connection = build_connection(rows=[row])

    with patch(
        "src.db.onboarding_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        invites = await onboarding_queries.list_invites(str(uuid4()))

    assert invites == [
        InviteResponse(
            id=invite_id,
            email="new.user@lekk.nl",
            role="inspector",
            is_accepted=False,
            created_at=created_at,
            expires_at=expires_at,
        )
    ]
    connection.close.assert_awaited_once()


async def test_delete_pending_invite_returns_true_when_deleted() -> None:
    connection = build_connection({"id": uuid4()})

    with patch(
        "src.db.onboarding_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        was_deleted = await onboarding_queries.delete_pending_invite(str(uuid4()), str(uuid4()))

    assert was_deleted is True
    connection.close.assert_awaited_once()
