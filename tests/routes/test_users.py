from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.exceptions import PasswordIncorrect
from src.main import app
from src.models.auth.authentication import CurrentUser
from src.security import authentication as security
from src.services import authentication as auth_service


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client


def build_current_user(name: str = "Inspector") -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="Demo Company",
        email="inspector@example.com",
        name=name,
        role="inspector",
    )


async def test_update_me_returns_updated_user(client: AsyncClient) -> None:
    current_user = build_current_user()
    updated_user = current_user.model_copy(update={"name": "Updated Inspector"})
    access_token = security.create_access_token(current_user)

    with (
        patch.object(
            auth_service.queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.users.users_service.update_profile",
            AsyncMock(return_value=updated_user),
        ) as update_profile,
    ):
        response = await client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": "  Updated Inspector  "},
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Inspector"
    update_profile.assert_awaited_once_with(current_user, "Updated Inspector")


async def test_update_me_rejects_long_name(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with patch.object(
        auth_service.queries,
        "get_user_by_id",
        AsyncMock(return_value=current_user),
    ):
        response = await client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": "A" * 101},
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "name must not exceed 100 characters"}


async def test_update_me_rejects_blank_name(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with patch.object(
        auth_service.queries,
        "get_user_by_id",
        AsyncMock(return_value=current_user),
    ):
        response = await client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": "   "},
        )

    assert response.status_code == 422


async def test_change_password_returns_no_content(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with (
        patch.object(
            auth_service.queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.users.users_service.change_password",
            AsyncMock(),
        ) as change_password,
    ):
        response = await client.post(
            "/api/v1/users/me/password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "current_password": "CurrentPassword2026!",
                "new_password": "NewPassword2026!",
            },
        )

    assert response.status_code == 204
    assert response.content == b""
    change_password.assert_awaited_once_with(
        str(current_user.id),
        "CurrentPassword2026!",
        "NewPassword2026!",
    )


async def test_change_password_rejects_short_new_password(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with patch.object(
        auth_service.queries,
        "get_user_by_id",
        AsyncMock(return_value=current_user),
    ):
        response = await client.post(
            "/api/v1/users/me/password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "current_password": "CurrentPassword2026!",
                "new_password": "short",
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "password_too_short"}


async def test_change_password_rejects_incorrect_current_password(
    client: AsyncClient,
) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with (
        patch.object(
            auth_service.queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.users.users_service.change_password",
            AsyncMock(side_effect=PasswordIncorrect()),
        ),
    ):
        response = await client.post(
            "/api/v1/users/me/password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "current_password": "WrongPassword2026!",
                "new_password": "NewPassword2026!",
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "current_password_incorrect"}


async def test_user_routes_require_access_token(client: AsyncClient) -> None:
    update_response = await client.patch("/api/v1/users/me", json={"name": "Inspector"})
    password_response = await client.post(
        "/api/v1/users/me/password",
        json={
            "current_password": "CurrentPassword2026!",
            "new_password": "NewPassword2026!",
        },
    )

    assert update_response.status_code == 401
    assert password_response.status_code == 401
