from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.models.auth.authentication import CurrentUser
from src.models.team.member import TeamMember
from src.security import authentication as security
from src.services import authentication as auth_service


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


async def test_list_team_members_returns_members(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)
    member_id = uuid4()
    created_at = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    member = TeamMember(
        id=member_id,
        name="Admin",
        email="admin@example.com",
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
            "src.routes.team.team.list_team_members",
            AsyncMock(return_value=[member]),
        ),
    ):
        response = await client.get(
            "/api/v1/team/members",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(member_id),
            "name": "Admin",
            "email": "admin@example.com",
            "role": "admin",
            "created_at": "2026-06-01T12:00:00Z",
        }
    ]


async def test_list_team_members_requires_admin(client: AsyncClient) -> None:
    current_user = build_inspector_user()
    access_token = security.create_access_token(current_user)

    with patch.object(
        auth_service.auth_queries,
        "get_user_by_id",
        AsyncMock(return_value=current_user),
    ):
        response = await client.get(
            "/api/v1/team/members",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Admin access required"}
