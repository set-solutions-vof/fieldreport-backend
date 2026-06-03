from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.exceptions import InviteAlreadyExists
from src.main import app
from src.models.auth.authentication import CurrentUser
from src.models.onboarding.company import CompanyOnboarding
from src.models.onboarding.invite import InviteCreated, InviteRecord
from src.security import authentication as security
from src.services import authentication as auth_service


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


def build_admin_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="Demo Company",
        email="admin@example.com",
        name="Admin",
        role="admin",
    )


def build_inspector_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="Demo Company",
        email="inspector@example.com",
        name="Inspector",
        role="inspector",
    )


async def test_get_onboarding_company_returns_company_state(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)
    company = CompanyOnboarding(
        id=current_user.company_id,
        name="Demo Company",
        logo_url="https://cdn.example/logo.png",
        primary_color="#3B5BDB",
        onboarding_completed=False,
    )

    with (
        patch.object(
            auth_service.auth_queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.onboarding.onboarding.get_company",
            AsyncMock(return_value=company),
        ),
    ):
        response = await client.get(
            "/api/v1/onboarding/company",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(current_user.company_id),
        "name": "Demo Company",
        "logo_url": "https://cdn.example/logo.png",
        "primary_color": "#3B5BDB",
        "onboarding_completed": False,
    }


async def test_patch_onboarding_company_updates_company_state(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)
    updated_company = CompanyOnboarding(
        id=current_user.company_id,
        name="Demo Company",
        logo_url=None,
        primary_color="#3B5BDB",
        onboarding_completed=True,
    )

    with (
        patch.object(
            auth_service.auth_queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.onboarding.onboarding.update_company",
            AsyncMock(return_value=updated_company),
        ) as update_company,
    ):
        response = await client.patch(
            "/api/v1/onboarding/company",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"primary_color": "#3B5BDB", "onboarding_completed": True},
        )

    assert response.status_code == 200
    assert response.json()["onboarding_completed"] is True
    update_company.assert_awaited_once()
    assert update_company.await_args.args[0] == str(current_user.company_id)
    update = update_company.await_args.args[1]
    assert update.primary_color == "#3B5BDB"
    assert update.onboarding_completed is True
    assert update.update_primary_color is True
    assert update.update_onboarding_completed is True


async def test_create_onboarding_invite_returns_created_invite(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)
    created_at = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    invite = InviteCreated(
        id=uuid4(),
        email="new.user@example.com",
        role="admin",
        created_at=created_at,
    )

    with (
        patch.object(
            auth_service.auth_queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.onboarding.onboarding.create_invite",
            AsyncMock(return_value=invite),
        ) as create_invite,
    ):
        response = await client.post(
            "/api/v1/onboarding/invites",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"email": "NEW.User@example.com", "role": "admin"},
        )

    assert response.status_code == 201
    assert response.json() == {
        "id": str(invite.id),
        "email": "new.user@example.com",
        "role": "admin",
        "created_at": "2026-06-01T12:00:00Z",
    }
    assert create_invite.await_args.args == (
        str(current_user.company_id),
        "NEW.User@example.com",
        "admin",
    )


async def test_create_onboarding_invite_rejects_duplicate_pending_invite(
    client: AsyncClient,
) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)

    with (
        patch.object(
            auth_service.auth_queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.onboarding.onboarding.create_invite",
            AsyncMock(side_effect=InviteAlreadyExists("new.user@example.com")),
        ),
    ):
        response = await client.post(
            "/api/v1/onboarding/invites",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"email": "new.user@example.com", "role": "inspector"},
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "Invite already exists"}


async def test_list_onboarding_invites_returns_company_invites(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)
    created_at = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    expires_at = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
    invite = InviteRecord(
        id=uuid4(),
        email="new.user@example.com",
        role="inspector",
        is_accepted=False,
        created_at=created_at,
        expires_at=expires_at,
    )

    with (
        patch.object(
            auth_service.auth_queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.onboarding.onboarding.list_invites",
            AsyncMock(return_value=[invite]),
        ),
    ):
        response = await client.get(
            "/api/v1/onboarding/invites",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(invite.id),
            "email": "new.user@example.com",
            "role": "inspector",
            "is_accepted": False,
            "created_at": "2026-06-01T12:00:00Z",
            "expires_at": "2026-06-08T12:00:00Z",
        }
    ]


async def test_delete_onboarding_invite_deletes_pending_invite(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)
    invite_id = uuid4()

    with (
        patch.object(
            auth_service.auth_queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.onboarding.onboarding.delete_pending_invite",
            AsyncMock(return_value=True),
        ) as delete_invite,
    ):
        response = await client.delete(
            f"/api/v1/onboarding/invites/{invite_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 204
    assert response.content == b""
    delete_invite.assert_awaited_once_with(str(current_user.company_id), str(invite_id))


async def test_delete_onboarding_invite_returns_not_found_for_missing_invite(
    client: AsyncClient,
) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)

    with (
        patch.object(
            auth_service.auth_queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.onboarding.onboarding.delete_pending_invite",
            AsyncMock(return_value=False),
        ),
    ):
        response = await client.delete(
            f"/api/v1/onboarding/invites/{uuid4()}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Invite not found"}


async def test_onboarding_routes_require_admin(client: AsyncClient) -> None:
    current_user = build_inspector_user()
    access_token = security.create_access_token(current_user)

    with patch.object(
        auth_service.auth_queries,
        "get_user_by_id",
        AsyncMock(return_value=current_user),
    ):
        response = await client.get(
            "/api/v1/onboarding/company",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Admin access required"}
