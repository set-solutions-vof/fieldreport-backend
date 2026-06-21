from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.db.onboarding import queries
from src.models.onboarding.company import CompanyOnboarding
from src.models.onboarding.invite import InviteCreated, InviteRecord
from src.models.onboarding.invite_details import InviteDetails
from tests.db.sqlalchemy_fakes import FakeResult, build_connection


def mock_pool(connection):
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return patch("src.db.onboarding.queries.get_database", return_value=pool)


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
        company = await queries.get_company(str(company_id))

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
        company = await queries.update_company(
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
    connection.execute.assert_awaited_once()


async def test_has_pending_invite_returns_true_for_existing_pending_invite() -> None:
    connection = build_connection({"id": uuid4()})

    with mock_pool(connection):
        has_pending_invite = await queries.has_pending_invite(
            str(uuid4()),
            "new.user@example.com",
        )

    assert has_pending_invite is True
    connection.execute.assert_awaited_once()


async def test_create_invite_returns_created_invite_response() -> None:
    invite_id = uuid4()
    created_at = datetime.now(UTC)
    expires_at = datetime.now(UTC)
    row = {
        "id": invite_id,
        "first_name": "New",
        "last_name": "User",
        "email": "new.user@example.com",
        "role": "admin",
        "created_at": created_at,
        "expires_at": expires_at,
    }
    connection = build_connection(row)

    with mock_pool(connection):
        invite = await queries.create_invite(
            str(uuid4()),
            "new.user@example.com",
            "admin",
            "token",
            expires_at,
            "New",
            "User",
        )

    assert invite == InviteCreated(
        id=invite_id,
        first_name="New",
        last_name="User",
        email="new.user@example.com",
        role="admin",
        created_at=created_at,
        expires_at=expires_at,
    )
    connection.execute.assert_awaited_once()


async def test_list_invites_returns_company_invites() -> None:
    created_at = datetime.now(UTC)
    expires_at = datetime.now(UTC)
    invite_id = uuid4()
    row = {
        "id": invite_id,
        "first_name": "New",
        "last_name": "User",
        "email": "new.user@example.com",
        "role": "inspector",
        "is_accepted": False,
        "created_at": created_at,
        "expires_at": expires_at,
    }
    connection = build_connection(rows=[row])

    with mock_pool(connection):
        invites = await queries.list_invites(str(uuid4()))

    assert invites == [
        InviteRecord(
            id=invite_id,
            first_name="New",
            last_name="User",
            email="new.user@example.com",
            role="inspector",
            is_accepted=False,
            created_at=created_at,
            expires_at=expires_at,
        )
    ]
    connection.execute.assert_awaited_once()


async def test_delete_pending_invite_returns_true_when_deleted() -> None:
    connection = build_connection({"id": uuid4()})

    with mock_pool(connection):
        was_deleted = await queries.delete_pending_invite(str(uuid4()), str(uuid4()))

    assert was_deleted is True
    connection.execute.assert_awaited_once()


async def test_get_invite_by_token_hash_returns_invite_details() -> None:
    invite_id = uuid4()
    company_id = uuid4()
    expires_at = datetime.now(UTC)
    row = {
        "id": invite_id,
        "company_id": company_id,
        "company_name": "Demo Company",
        "first_name": "New",
        "last_name": "User",
        "email": "new.user@example.com",
        "role": "admin",
        "is_accepted": False,
        "expires_at": expires_at,
    }
    connection = build_connection(row)

    with mock_pool(connection):
        invite = await queries.get_invite_by_token_hash("token-hash")

    assert invite == InviteDetails(
        id=invite_id,
        first_name="New",
        last_name="User",
        company_id=company_id,
        company_name="Demo Company",
        email="new.user@example.com",
        role="admin",
        is_accepted=False,
        expires_at=expires_at,
    )
    connection.execute.assert_awaited_once()


async def test_get_invite_by_token_hash_returns_none_when_missing() -> None:
    connection = build_connection(None)

    with mock_pool(connection):
        invite = await queries.get_invite_by_token_hash("missing-token")

    assert invite is None
    connection.execute.assert_awaited_once()


async def test_accept_invite_and_create_user_returns_user_id() -> None:
    invite_id = uuid4()
    user_id = uuid4()
    connection = build_connection(
        results=[
            FakeResult(row={"id": invite_id}),
            FakeResult(row={"id": user_id}),
            FakeResult(),
        ]
    )
    transaction = MagicMock()
    transaction.__aenter__ = AsyncMock(return_value=None)
    transaction.__aexit__ = AsyncMock(return_value=None)
    connection.transaction = MagicMock(return_value=transaction)

    with mock_pool(connection):
        result = await queries.accept_invite_and_create_user(
            str(invite_id),
            str(uuid4()),
            "new.user@example.com",
            "New",
            "User",
            "inspector",
            "hashed-password",
        )

    assert result == str(user_id)
    assert connection.execute.await_count == 3


async def test_accept_invite_and_create_user_returns_empty_string_when_invite_missing() -> None:
    connection = build_connection(None)
    transaction = MagicMock()
    transaction.__aenter__ = AsyncMock(return_value=None)
    transaction.__aexit__ = AsyncMock(return_value=None)
    connection.transaction = MagicMock(return_value=transaction)

    with mock_pool(connection):
        result = await queries.accept_invite_and_create_user(
            str(uuid4()),
            str(uuid4()),
            "new.user@example.com",
            "New",
            "User",
            "inspector",
            "hashed-password",
        )

    assert result == ""
    connection.execute.assert_awaited_once()


async def test_get_pending_invite_returns_invite() -> None:
    invite_id = uuid4()
    created_at = datetime.now(UTC)
    expires_at = datetime.now(UTC)
    row = {
        "id": invite_id,
        "first_name": "New",
        "last_name": "User",
        "email": "new.user@example.com",
        "role": "inspector",
        "is_accepted": False,
        "created_at": created_at,
        "expires_at": expires_at,
    }
    connection = build_connection(row)

    with mock_pool(connection):
        invite = await queries.get_pending_invite(str(uuid4()), str(invite_id))

    assert invite is not None
    assert invite.email == "new.user@example.com"
    connection.execute.assert_awaited_once()


async def test_get_pending_invite_returns_none_when_missing() -> None:
    connection = build_connection(None)

    with mock_pool(connection):
        invite = await queries.get_pending_invite(str(uuid4()), str(uuid4()))

    assert invite is None
    connection.execute.assert_awaited_once()


async def test_update_pending_invite_returns_updated_invite() -> None:
    invite_id = uuid4()
    created_at = datetime.now(UTC)
    expires_at = datetime.now(UTC)
    row = {
        "id": invite_id,
        "first_name": "Updated",
        "last_name": "User",
        "email": "new.user@example.com",
        "role": "admin",
        "is_accepted": False,
        "created_at": created_at,
        "expires_at": expires_at,
    }
    connection = build_connection(row)

    with mock_pool(connection):
        invite = await queries.update_pending_invite(
            str(uuid4()),
            str(invite_id),
            "Updated",
            "User",
            "admin",
        )

    assert invite is not None
    assert invite.role == "admin"
    connection.execute.assert_awaited_once()


async def test_update_pending_invite_returns_none_when_missing() -> None:
    connection = build_connection(None)

    with mock_pool(connection):
        invite = await queries.update_pending_invite(
            str(uuid4()),
            str(uuid4()),
            "Updated",
            "User",
            "admin",
        )

    assert invite is None
    connection.execute.assert_awaited_once()
