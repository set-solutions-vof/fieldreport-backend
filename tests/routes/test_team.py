from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.exceptions import InviteAlreadyExists, InviteEmailDeliveryFailed
from src.main import app
from src.models.auth.authentication import CurrentUser
from src.models.team.user import TeamUser
from src.security import authentication as security
from src.services import authentication as auth_service
from src.services import invites


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def build_admin_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="Demo Company",
        email="admin@example.com",
        first_name="Admin",
        last_name="",
        role="admin",
    )


def build_inspector_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="Demo Company",
        email="inspector@example.com",
        first_name="Inspector",
        last_name="",
        role="inspector",
    )


async def test_list_team_users_returns_users(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)
    user_id = uuid4()
    created_at = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    team_user = TeamUser(
        id=user_id,
        first_name="Admin",
        last_name="",
        email="admin@example.com",
        role="admin",
        status="active",
        created_at=created_at,
        last_sign_in_at=None,
    )

    with (
        patch.object(
            auth_service.queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.team.team.list_team_users",
            AsyncMock(return_value=[team_user]),
        ),
    ):
        response = await client.get(
            "/api/v1/team/users",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(user_id),
            "first_name": "Admin",
            "last_name": "",
            "email": "admin@example.com",
            "role": "admin",
            "status": "active",
            "created_at": "2026-06-01T12:00:00Z",
            "last_sign_in_at": None,
        }
    ]


async def test_list_team_users_requires_admin(client: AsyncClient) -> None:
    current_user = build_inspector_user()
    access_token = security.create_access_token(current_user)

    with patch.object(
        auth_service.queries,
        "get_user_by_id",
        AsyncMock(return_value=current_user),
    ):
        response = await client.get(
            "/api/v1/team/users",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Admin access required"}


async def test_create_team_user_returns_invited_user(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)
    user_id = uuid4()
    created_at = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    team_user = TeamUser(
        id=user_id,
        first_name="New",
        last_name="User",
        email="new.user@example.com",
        role="inspector",
        status="invited",
        created_at=created_at,
        last_sign_in_at=None,
    )
    email_delivery = invites.InviteEmailDelivery(
        company_id=str(current_user.company_id),
        invite_id=str(user_id),
        to_email="new.user@example.com",
        company_name="Demo Company",
        role="inspector",
        token="raw-token",
    )

    with (
        patch.object(
            auth_service.queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.team.team.create_team_user",
            AsyncMock(return_value=(team_user, email_delivery)),
        ),
        patch(
            "src.routes.team.invites.deliver_invite_email",
            AsyncMock(),
        ) as deliver_invite_email,
    ):
        response = await client.post(
            "/api/v1/team/users",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "first_name": "New",
                "last_name": "User",
                "email": "new.user@example.com",
                "role": "inspector",
            },
        )

    assert response.status_code == 201
    assert response.json()["status"] == "invited"
    deliver_invite_email.assert_awaited_once_with(email_delivery)


async def test_create_team_user_rejects_blank_names(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)

    with patch.object(
        auth_service.queries,
        "get_user_by_id",
        AsyncMock(return_value=current_user),
    ):
        response = await client.post(
            "/api/v1/team/users",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "first_name": " ",
                "last_name": "User",
                "email": "new.user@example.com",
                "role": "inspector",
            },
        )

    assert response.status_code == 422


async def test_create_team_user_returns_conflict_when_invite_exists(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)

    with (
        patch.object(
            auth_service.queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.team.team.create_team_user",
            AsyncMock(side_effect=InviteAlreadyExists("new.user@example.com")),
        ),
    ):
        response = await client.post(
            "/api/v1/team/users",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "first_name": "New",
                "last_name": "User",
                "email": "new.user@example.com",
                "role": "inspector",
            },
        )

    assert response.status_code == 409


async def test_create_team_user_returns_bad_gateway_when_email_fails(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)

    with (
        patch.object(
            auth_service.queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.team.team.create_team_user",
            AsyncMock(side_effect=InviteEmailDeliveryFailed()),
        ),
    ):
        response = await client.post(
            "/api/v1/team/users",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "first_name": "New",
                "last_name": "User",
                "email": "new.user@example.com",
                "role": "inspector",
            },
        )

    assert response.status_code == 502


async def test_get_team_user_returns_user(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)
    user_id = uuid4()
    team_user = TeamUser(
        id=user_id,
        first_name="Admin",
        last_name="",
        email="admin@example.com",
        role="admin",
        status="active",
        created_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
        last_sign_in_at=None,
    )

    with (
        patch.object(
            auth_service.queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.team.team.get_team_user",
            AsyncMock(return_value=team_user),
        ),
    ):
        response = await client.get(
            f"/api/v1/team/users/{user_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    assert response.json()["id"] == str(user_id)


async def test_get_team_user_returns_not_found(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)

    with (
        patch.object(
            auth_service.queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.team.team.get_team_user",
            AsyncMock(return_value=None),
        ),
    ):
        response = await client.get(
            f"/api/v1/team/users/{uuid4()}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 404


async def test_update_team_user_returns_updated_user(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)
    user_id = uuid4()
    team_user = TeamUser(
        id=user_id,
        first_name="Updated",
        last_name="User",
        email="admin@example.com",
        role="inspector",
        status="active",
        created_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
        last_sign_in_at=None,
    )

    with (
        patch.object(
            auth_service.queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.team.team.update_team_user",
            AsyncMock(return_value=team_user),
        ),
    ):
        response = await client.patch(
            f"/api/v1/team/users/{user_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "first_name": "Updated",
                "last_name": "User",
                "role": "inspector",
            },
        )

    assert response.status_code == 200
    assert response.json()["first_name"] == "Updated"


async def test_update_team_user_returns_not_found(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)

    with (
        patch.object(
            auth_service.queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.team.team.update_team_user",
            AsyncMock(return_value=None),
        ),
    ):
        response = await client.patch(
            f"/api/v1/team/users/{uuid4()}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "first_name": "Updated",
                "last_name": "User",
                "role": "inspector",
            },
        )

    assert response.status_code == 404


async def test_delete_team_user_returns_no_content(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)
    user_id = uuid4()

    with (
        patch.object(
            auth_service.queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.team.team.delete_team_user",
            AsyncMock(return_value=True),
        ),
    ):
        response = await client.delete(
            f"/api/v1/team/users/{user_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 204


async def test_delete_team_user_rejects_self_delete(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)

    with patch.object(
        auth_service.queries,
        "get_user_by_id",
        AsyncMock(return_value=current_user),
    ):
        response = await client.delete(
            f"/api/v1/team/users/{current_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 400


async def test_delete_team_user_returns_not_found(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)

    with (
        patch.object(
            auth_service.queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.team.team.delete_team_user",
            AsyncMock(return_value=False),
        ),
    ):
        response = await client.delete(
            f"/api/v1/team/users/{uuid4()}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 404


async def test_update_team_user_rejects_blank_names(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)

    with patch.object(
        auth_service.queries,
        "get_user_by_id",
        AsyncMock(return_value=current_user),
    ):
        response = await client.patch(
            f"/api/v1/team/users/{uuid4()}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "first_name": " ",
                "last_name": "User",
                "role": "inspector",
            },
        )

    assert response.status_code == 422
