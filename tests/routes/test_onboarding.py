from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.http.v1.response.onboarding import (
    CompanyOnboardingResponse,
    InviteCreatedResponse,
    InviteResponse,
)
from src.main import app
from src.models.auth.authentication import CurrentUser
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
        company_name="LEKK BV",
        email="admin@lekk.nl",
        name="Admin",
        role="admin",
    )


def build_inspector_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="LEKK BV",
        email="inspector@lekk.nl",
        name="Inspector",
        role="inspector",
    )


async def test_get_onboarding_company_returns_company_state(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)
    company = CompanyOnboardingResponse(
        id=current_user.company_id,
        name="LEKK BV",
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
            "src.routes.onboarding.onboarding_queries.get_company",
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
        "name": "LEKK BV",
        "logo_url": "https://cdn.example/logo.png",
        "primary_color": "#3B5BDB",
        "onboarding_completed": False,
    }


async def test_patch_onboarding_company_updates_company_state(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)
    updated_company = CompanyOnboardingResponse(
        id=current_user.company_id,
        name="LEKK BV",
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
            "src.routes.onboarding.onboarding_queries.update_company",
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
    update_company.assert_awaited_once_with(
        str(current_user.company_id),
        None,
        "#3B5BDB",
        True,
        False,
        True,
        True,
    )


async def test_create_onboarding_invite_returns_created_invite(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)
    created_at = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    invite = InviteCreatedResponse(
        id=uuid4(),
        email="new.user@lekk.nl",
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
            "src.routes.onboarding.onboarding_queries.has_pending_invite",
            AsyncMock(return_value=False),
        ),
        patch(
            "src.routes.onboarding.onboarding_queries.create_invite",
            AsyncMock(return_value=invite),
        ) as create_invite,
        patch("src.routes.onboarding.secrets.token_hex", return_value="token"),
    ):
        response = await client.post(
            "/api/v1/onboarding/invites",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"email": "NEW.User@LEKK.nl", "role": "admin"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(invite.id),
        "email": "new.user@lekk.nl",
        "role": "admin",
        "created_at": "2026-06-01T12:00:00Z",
    }
    assert create_invite.await_args.args[1:4] == ("NEW.User@LEKK.nl", "admin", "token")


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
            "src.routes.onboarding.onboarding_queries.has_pending_invite",
            AsyncMock(return_value=True),
        ),
    ):
        response = await client.post(
            "/api/v1/onboarding/invites",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"email": "new.user@lekk.nl", "role": "inspector"},
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "Invite already exists"}


async def test_list_onboarding_invites_returns_company_invites(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)
    created_at = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    expires_at = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
    invite = InviteResponse(
        id=uuid4(),
        email="new.user@lekk.nl",
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
            "src.routes.onboarding.onboarding_queries.list_invites",
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
            "email": "new.user@lekk.nl",
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
            "src.routes.onboarding.onboarding_queries.delete_pending_invite",
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
            "src.routes.onboarding.onboarding_queries.delete_pending_invite",
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
