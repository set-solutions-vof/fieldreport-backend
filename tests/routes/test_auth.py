from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.models.auth.authentication import AuthenticatedUser, CurrentUser
from src.security import authentication as security
from src.services import authentication as service


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def build_authenticated_user() -> AuthenticatedUser:
    password_hash = bcrypt.hashpw(b"LekkDemo2026!", bcrypt.gensalt()).decode()

    return AuthenticatedUser(
        id=uuid4(),
        company_id=uuid4(),
        email="sanne.devries@lekk.nl",
        password_hash=password_hash,
        name="Sanne de Vries",
        role="admin",
    )


def build_current_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        email="jeroen.vandijk@lekk.nl",
        name="Jeroen van Dijk",
        role="inspector",
    )


async def test_login_json_returns_tokens_for_valid_credentials(client: AsyncClient) -> None:
    authenticated_user = build_authenticated_user()

    with patch.object(
        service.auth_repository, "get_user_by_email", AsyncMock(return_value=authenticated_user)
    ):
        response = await client.post(
            "/api/v1/auth/login/json",
            json={"email": authenticated_user.email, "password": "LekkDemo2026!"},
        )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()


async def test_login_form_returns_tokens_for_valid_credentials(client: AsyncClient) -> None:
    authenticated_user = build_authenticated_user()

    with patch.object(
        service.auth_repository, "get_user_by_email", AsyncMock(return_value=authenticated_user)
    ):
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": authenticated_user.email, "password": "LekkDemo2026!"},
        )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


async def test_login_returns_unauthorized_for_wrong_password(client: AsyncClient) -> None:
    authenticated_user = build_authenticated_user()

    with patch.object(
        service.auth_repository, "get_user_by_email", AsyncMock(return_value=authenticated_user)
    ):
        response = await client.post(
            "/api/v1/auth/login/json",
            json={"email": authenticated_user.email, "password": "wrong-password"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


async def test_login_form_returns_unauthorized_for_wrong_password(client: AsyncClient) -> None:
    authenticated_user = build_authenticated_user()

    with patch.object(
        service.auth_repository, "get_user_by_email", AsyncMock(return_value=authenticated_user)
    ):
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": authenticated_user.email, "password": "wrong-password"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


async def test_refresh_returns_new_access_token(client: AsyncClient) -> None:
    current_user = build_current_user()
    refresh_token = security.create_refresh_token(current_user)

    with patch.object(
        service.auth_repository, "get_user_by_id", AsyncMock(return_value=current_user)
    ):
        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert "access_token" in response.json()


async def test_refresh_rejects_invalid_token(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


async def test_me_requires_access_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


async def test_me_returns_authenticated_user(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with patch.object(
        service.auth_repository, "get_user_by_id", AsyncMock(return_value=current_user)
    ):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "company_id": str(current_user.company_id),
    }


async def test_reports_require_access_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/reports")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


async def test_reports_accept_access_token(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with patch.object(
        service.auth_repository, "get_user_by_id", AsyncMock(return_value=current_user)
    ):
        response = await client.get(
            "/api/v1/reports",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "demo-report",
            "company_id": str(current_user.company_id),
            "status": "draft",
        }
    ]
