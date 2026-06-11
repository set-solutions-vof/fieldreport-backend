from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.exceptions import InviteInvalid
from src.main import app
from src.models.auth.authentication import TokenPair
from src.models.onboarding.invite_preview import InvitePreview


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_get_invite_preview_returns_preview(client: AsyncClient) -> None:
    with patch(
        "src.routes.invites.invites.get_invite_preview",
        AsyncMock(
            return_value=InvitePreview(
                email="new.user@example.com",
                role="inspector",
                company_name="Demo Company",
            )
        ),
    ):
        response = await client.get("/api/v1/invites/raw-token")

    assert response.status_code == 200
    assert response.json() == {
        "email": "new.user@example.com",
        "role": "inspector",
        "company_name": "Demo Company",
    }


async def test_get_invite_preview_returns_not_found_for_invalid_invite(
    client: AsyncClient,
) -> None:
    with patch(
        "src.routes.invites.invites.get_invite_preview",
        AsyncMock(side_effect=InviteInvalid()),
    ):
        response = await client.get("/api/v1/invites/invalid-token")

    assert response.status_code == 404
    assert response.json() == {"detail": "Invite not found"}


async def test_accept_invite_returns_tokens(client: AsyncClient) -> None:
    with patch(
        "src.routes.invites.invites.accept_invite",
        AsyncMock(
            return_value=TokenPair(
                access_token="access-token",
                refresh_token="refresh-token",
                token_type="bearer",
            )
        ),
    ) as accept_invite:
        response = await client.post(
            "/api/v1/invites/raw-token/accept",
            json={"name": "New User", "password": "secret"},
        )

    assert response.status_code == 201
    assert response.json() == {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "token_type": "bearer",
    }
    accept_invite.assert_awaited_once_with("raw-token", "New User", "secret")


async def test_accept_invite_returns_bad_request_for_invalid_invite(
    client: AsyncClient,
) -> None:
    with patch(
        "src.routes.invites.invites.accept_invite",
        AsyncMock(side_effect=InviteInvalid()),
    ):
        response = await client.post(
            f"/api/v1/invites/{uuid4()}/accept",
            json={"name": "New User", "password": "secret"},
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invite is invalid"}
