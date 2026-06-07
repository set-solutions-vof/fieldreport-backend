from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.db import onboarding_queries
from src.models.onboarding.company import CompanyOnboarding
from src.models.onboarding.invite import InviteCreated, InviteRecord
from src.models.onboarding.invite_details import InviteDetails


def build_connection(
    row: dict[str, object] | None = None,
    rows: list[dict[str, object]] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        fetchrow=AsyncMock(return_value=row),
        fetch=AsyncMock(return_value=rows or []),
    )


def mock_pool(connection):
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return patch("src.db.onboarding_queries.get_pool", return_value=pool)


async def test_get_company_returns_company_response() -> None:
    company_id = uuid4()
    row = {
        "id": company_id,
        "name": "Demo Company",
        "logo_url": None,
        "primary_color": "#3B5BDB",
        "onboarding_completed": False,
    }
    connection = build_connection(row)

    with mock_pool(connection):
        company = await onboarding_queries.get_company(str(company_id))

    assert company == CompanyOnboarding(
        id=company_id,
        name="Demo Company",
        logo_url=None,
        primary_color="#3B5BDB",
        onboarding_completed=False,
    )


async def test_update_company_returns_updated_company_response() -> None:
    company_id = uuid4()
    row = {
        "id": company_id,
        "name": "Demo Company",
        "logo_url": "https://cdn.example/logo.png",
        "primary_color": "#3B5BDB",
        "onboarding_completed": True,
    }
    connection = build_connection(row)

    with mock_pool(connection):
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


async def test_has_pending_invite_returns_true_for_existing_pending_invite() -> None:
    connection = build_connection({"id": uuid4()})

    with mock_pool(connection):
        has_pending_invite = await onboarding_queries.has_pending_invite(
            str(uuid4()),
            "new.user@example.com",
        )

    assert has_pending_invite is True


async def test_create_invite_returns_created_invite_response() -> None:
    invite_id = uuid4()
    created_at = datetime.now(UTC)
    expires_at = datetime.now(UTC)
    row = {
        "id": invite_id,
        "email": "new.user@example.com",
        "role": "admin",
        "created_at": created_at,
    }
    connection = build_connection(row)

    with mock_pool(connection):
        invite = await onboarding_queries.create_invite(
            str(uuid4()),
            "new.user@example.com",
            "admin",
            "token",
            expires_at,
        )

    assert invite == InviteCreated(
        id=invite_id,
        email="new.user@example.com",
        role="admin",
        created_at=created_at,
    )


async def test_list_invites_returns_company_invites() -> None:
    created_at = datetime.now(UTC)
    expires_at = datetime.now(UTC)
    invite_id = uuid4()
    row = {
        "id": invite_id,
        "email": "new.user@example.com",
        "role": "inspector",
        "is_accepted": False,
        "created_at": created_at,
        "expires_at": expires_at,
    }
    connection = build_connection(rows=[row])

    with mock_pool(connection):
        invites = await onboarding_queries.list_invites(str(uuid4()))

    assert invites == [
        InviteRecord(
            id=invite_id,
            email="new.user@example.com",
            role="inspector",
            is_accepted=False,
            created_at=created_at,
            expires_at=expires_at,
        )
    ]


async def test_delete_pending_invite_returns_true_when_deleted() -> None:
    connection = build_connection({"id": uuid4()})

    with mock_pool(connection):
        was_deleted = await onboarding_queries.delete_pending_invite(str(uuid4()), str(uuid4()))

    assert was_deleted is True


async def test_get_invite_by_token_hash_returns_invite_details() -> None:
    invite_id = uuid4()
    company_id = uuid4()
    expires_at = datetime.now(UTC)
    row = {
        "id": invite_id,
        "company_id": company_id,
        "company_name": "Demo Company",
        "email": "new.user@example.com",
        "role": "admin",
        "is_accepted": False,
        "expires_at": expires_at,
    }
    connection = build_connection(row)

    with mock_pool(connection):
        invite = await onboarding_queries.get_invite_by_token_hash("token-hash")

    assert invite == InviteDetails(
        id=invite_id,
        company_id=company_id,
        company_name="Demo Company",
        email="new.user@example.com",
        role="admin",
        is_accepted=False,
        expires_at=expires_at,
    )


async def test_get_invite_by_token_hash_returns_none_when_missing() -> None:
    connection = build_connection(None)

    with mock_pool(connection):
        invite = await onboarding_queries.get_invite_by_token_hash("missing-token")

    assert invite is None


async def test_accept_invite_and_create_user_returns_user_id() -> None:
    invite_id = uuid4()
    user_id = uuid4()
    connection = build_connection(None)
    connection.fetchrow = AsyncMock(side_effect=[{"id": invite_id}, {"id": user_id}])
    connection.execute = AsyncMock()
    transaction = MagicMock()
    transaction.__aenter__ = AsyncMock(return_value=None)
    transaction.__aexit__ = AsyncMock(return_value=None)
    connection.transaction = MagicMock(return_value=transaction)

    with mock_pool(connection):
        result = await onboarding_queries.accept_invite_and_create_user(
            str(invite_id),
            str(uuid4()),
            "new.user@example.com",
            "New User",
            "inspector",
            "hashed-password",
        )

    assert result == str(user_id)


async def test_accept_invite_and_create_user_returns_empty_string_when_invite_missing() -> None:
    connection = build_connection(None)
    connection.fetchrow = AsyncMock(return_value=None)
    transaction = MagicMock()
    transaction.__aenter__ = AsyncMock(return_value=None)
    transaction.__aexit__ = AsyncMock(return_value=None)
    connection.transaction = MagicMock(return_value=transaction)

    with mock_pool(connection):
        result = await onboarding_queries.accept_invite_and_create_user(
            str(uuid4()),
            str(uuid4()),
            "new.user@example.com",
            "New User",
            "inspector",
            "hashed-password",
        )

    assert result == ""
