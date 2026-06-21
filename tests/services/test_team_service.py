from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.models.onboarding.invite import InviteCreated, InviteRecord
from src.models.team.member import TeamMember
from src.services import team as team_service
from src.services.invites import InviteEmailDelivery


def build_member() -> TeamMember:
    return TeamMember(
        id=uuid4(),
        first_name="Admin",
        last_name="User",
        email="admin@example.com",
        role="admin",
        created_at=datetime.now(UTC),
    )


def build_invite() -> InviteRecord:
    return InviteRecord(
        id=uuid4(),
        first_name="New",
        last_name="User",
        email="new.user@example.com",
        role="inspector",
        is_accepted=False,
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
    )


def build_created_invite() -> InviteCreated:
    return InviteCreated(
        id=uuid4(),
        first_name="New",
        last_name="User",
        email="new.user@example.com",
        role="inspector",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
    )


async def test_list_team_users_includes_pending_invites() -> None:
    member = build_member()
    invite = build_invite()

    with (
        patch.object(
            team_service.queries,
            "list_company_members",
            AsyncMock(return_value=[member]),
        ),
        patch.object(
            team_service.onboarding_queries,
            "list_invites",
            AsyncMock(return_value=[invite, invite.model_copy(update={"is_accepted": True})]),
        ),
    ):
        result = await team_service.list_team_users(str(uuid4()))

    assert len(result) == 2
    assert result[0].status == "active"
    assert result[1].status == "invited"


async def test_create_team_user_returns_invited_user_and_delivery() -> None:
    invite = build_created_invite()
    delivery = InviteEmailDelivery(
        company_id=str(uuid4()),
        invite_id=str(invite.id),
        to_email=invite.email,
        company_name="Demo Company",
        role="inspector",
        token="token",
    )

    with patch.object(
        team_service.invites_service,
        "create_invite",
        AsyncMock(return_value=(invite, delivery)),
    ):
        user, returned_delivery = await team_service.create_team_user(
            str(uuid4()),
            "New",
            "User",
            invite.email,
            "inspector",
        )

    assert user.status == "invited"
    assert returned_delivery == delivery


async def test_get_team_user_returns_member() -> None:
    member = build_member()

    with (
        patch.object(
            team_service.queries,
            "get_company_member",
            AsyncMock(return_value=member),
        ),
        patch.object(
            team_service.onboarding_queries,
            "get_pending_invite",
            AsyncMock(),
        ) as get_pending_invite,
    ):
        result = await team_service.get_team_user(str(uuid4()), str(member.id))

    assert result is not None
    assert result.status == "active"
    get_pending_invite.assert_not_awaited()


async def test_get_team_user_returns_pending_invite() -> None:
    invite = build_invite()

    with (
        patch.object(
            team_service.queries,
            "get_company_member",
            AsyncMock(return_value=None),
        ),
        patch.object(
            team_service.onboarding_queries,
            "get_pending_invite",
            AsyncMock(return_value=invite),
        ),
    ):
        result = await team_service.get_team_user(str(uuid4()), str(invite.id))

    assert result is not None
    assert result.status == "invited"


async def test_get_team_user_returns_none_when_missing() -> None:
    with (
        patch.object(
            team_service.queries,
            "get_company_member",
            AsyncMock(return_value=None),
        ),
        patch.object(
            team_service.onboarding_queries,
            "get_pending_invite",
            AsyncMock(return_value=None),
        ),
    ):
        result = await team_service.get_team_user(str(uuid4()), str(uuid4()))

    assert result is None


async def test_update_team_user_updates_member() -> None:
    member = build_member()

    with (
        patch.object(
            team_service.queries,
            "update_company_member",
            AsyncMock(return_value=member),
        ),
        patch.object(
            team_service.onboarding_queries,
            "update_pending_invite",
            AsyncMock(),
        ) as update_pending_invite,
    ):
        result = await team_service.update_team_user(
            str(uuid4()),
            str(member.id),
            "Admin",
            "User",
            "admin",
        )

    assert result is not None
    assert result.status == "active"
    update_pending_invite.assert_not_awaited()


async def test_update_team_user_updates_pending_invite() -> None:
    invite = build_invite()

    with (
        patch.object(
            team_service.queries,
            "update_company_member",
            AsyncMock(return_value=None),
        ),
        patch.object(
            team_service.onboarding_queries,
            "update_pending_invite",
            AsyncMock(return_value=invite),
        ),
    ):
        result = await team_service.update_team_user(
            str(uuid4()),
            str(invite.id),
            "New",
            "User",
            "inspector",
        )

    assert result is not None
    assert result.status == "invited"


async def test_update_team_user_returns_none_when_missing() -> None:
    with (
        patch.object(
            team_service.queries,
            "update_company_member",
            AsyncMock(return_value=None),
        ),
        patch.object(
            team_service.onboarding_queries,
            "update_pending_invite",
            AsyncMock(return_value=None),
        ),
    ):
        result = await team_service.update_team_user(
            str(uuid4()),
            str(uuid4()),
            "New",
            "User",
            "inspector",
        )

    assert result is None


async def test_delete_team_user_deletes_member() -> None:
    with (
        patch.object(
            team_service.queries,
            "delete_company_member",
            AsyncMock(return_value=True),
        ),
        patch.object(
            team_service.onboarding_queries,
            "delete_pending_invite",
            AsyncMock(),
        ) as delete_pending_invite,
    ):
        result = await team_service.delete_team_user(str(uuid4()), str(uuid4()))

    assert result is True
    delete_pending_invite.assert_not_awaited()


async def test_delete_team_user_deletes_pending_invite() -> None:
    with (
        patch.object(
            team_service.queries,
            "delete_company_member",
            AsyncMock(return_value=False),
        ),
        patch.object(
            team_service.onboarding_queries,
            "delete_pending_invite",
            AsyncMock(return_value=True),
        ),
    ):
        result = await team_service.delete_team_user(str(uuid4()), str(uuid4()))

    assert result is True
