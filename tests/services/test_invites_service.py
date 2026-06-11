from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from asyncpg import UniqueViolationError
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.exceptions import InviteInvalid
from src.models.auth.authentication import CurrentUser
from src.models.onboarding.invite_details import InviteDetails
from src.models.onboarding.invite_preview import InvitePreview
from src.services import invites as invites_service


def build_invite_details(*, is_accepted: bool = False) -> InviteDetails:
    return InviteDetails(
        id=uuid4(),
        company_id=uuid4(),
        company_name="Demo Company",
        email="new.user@example.com",
        role="inspector",
        is_accepted=is_accepted,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )


async def test_get_invite_preview_returns_preview() -> None:
    invite = build_invite_details()

    with patch.object(
        invites_service.queries,
        "get_invite_by_token_hash",
        AsyncMock(return_value=invite),
    ):
        result = await invites_service.get_invite_preview("token")

    assert result == InvitePreview(
        email="new.user@example.com",
        role="inspector",
        company_name="Demo Company",
    )


async def test_get_invite_preview_raises_for_invalid_invite() -> None:
    with patch.object(
        invites_service.queries,
        "get_invite_by_token_hash",
        AsyncMock(return_value=None),
    ):
        with pytest.raises(InviteInvalid):
            await invites_service.get_invite_preview("token")


async def test_accept_invite_returns_tokens() -> None:
    invite = build_invite_details()
    current_user = CurrentUser(
        id=uuid4(),
        company_id=invite.company_id,
        company_name="Demo Company",
        email=invite.email,
        name="New User",
        role="inspector",
    )

    with (
        patch.object(
            invites_service.queries,
            "get_invite_by_token_hash",
            AsyncMock(return_value=invite),
        ),
        patch(
            "src.services.invites.get_user_by_email",
            AsyncMock(return_value=None),
        ),
        patch.object(
            invites_service.queries,
            "accept_invite_and_create_user",
            AsyncMock(return_value=str(current_user.id)),
        ),
        patch(
            "src.services.invites.get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch.object(
            invites_service.authentication,
            "hash_password",
            return_value="hashed-password",
        ),
        patch.object(
            invites_service.authentication,
            "create_access_token",
            return_value="access-token",
        ),
        patch.object(
            invites_service.authentication,
            "create_refresh_token",
            return_value="refresh-token",
        ),
    ):
        result = await invites_service.accept_invite("token", "New User", "secret")

    assert result.access_token == "access-token"
    assert result.refresh_token == "refresh-token"


async def test_get_invite_preview_raises_for_accepted_invite() -> None:
    invite = build_invite_details(is_accepted=True)

    with patch.object(
        invites_service.queries,
        "get_invite_by_token_hash",
        AsyncMock(return_value=invite),
    ):
        with pytest.raises(InviteInvalid):
            await invites_service.get_invite_preview("token")


async def test_get_invite_preview_raises_for_expired_invite() -> None:
    invite = build_invite_details()
    invite = invite.model_copy(update={"expires_at": datetime.now(UTC) - timedelta(seconds=1)})

    with patch.object(
        invites_service.queries,
        "get_invite_by_token_hash",
        AsyncMock(return_value=invite),
    ):
        with pytest.raises(InviteInvalid):
            await invites_service.get_invite_preview("token")


async def test_accept_invite_raises_when_user_already_exists() -> None:
    invite = build_invite_details()
    existing_user = CurrentUser(
        id=uuid4(),
        company_id=invite.company_id,
        company_name="Demo Company",
        email=invite.email,
        name="Existing User",
        role="inspector",
    )

    with (
        patch.object(
            invites_service.queries,
            "get_invite_by_token_hash",
            AsyncMock(return_value=invite),
        ),
        patch(
            "src.services.invites.get_user_by_email",
            AsyncMock(return_value=existing_user),
        ),
    ):
        with pytest.raises(InviteInvalid):
            await invites_service.accept_invite("token", "New User", "secret")


async def test_accept_invite_raises_when_created_user_cannot_be_loaded() -> None:
    invite = build_invite_details()
    user_id = uuid4()

    with (
        patch.object(
            invites_service.queries,
            "get_invite_by_token_hash",
            AsyncMock(return_value=invite),
        ),
        patch(
            "src.services.invites.get_user_by_email",
            AsyncMock(return_value=None),
        ),
        patch.object(
            invites_service.queries,
            "accept_invite_and_create_user",
            AsyncMock(return_value=str(user_id)),
        ),
        patch(
            "src.services.invites.get_user_by_id",
            AsyncMock(return_value=None),
        ),
    ):
        with pytest.raises(InviteInvalid):
            await invites_service.accept_invite("token", "New User", "secret")


async def test_accept_invite_raises_when_user_creation_fails() -> None:
    invite = build_invite_details()

    with (
        patch.object(
            invites_service.queries,
            "get_invite_by_token_hash",
            AsyncMock(return_value=invite),
        ),
        patch(
            "src.services.invites.get_user_by_email",
            AsyncMock(return_value=None),
        ),
        patch.object(
            invites_service.queries,
            "accept_invite_and_create_user",
            AsyncMock(return_value=""),
        ),
    ):
        with pytest.raises(InviteInvalid):
            await invites_service.accept_invite("token", "New User", "secret")


async def test_accept_invite_returns_conflict_for_asyncpg_unique_violation() -> None:
    invite = build_invite_details()

    with (
        patch.object(
            invites_service.queries,
            "get_invite_by_token_hash",
            AsyncMock(return_value=invite),
        ),
        patch(
            "src.services.invites.get_user_by_email",
            AsyncMock(return_value=None),
        ),
        patch.object(
            invites_service.queries,
            "accept_invite_and_create_user",
            AsyncMock(side_effect=UniqueViolationError("duplicate")),
        ),
    ):
        with pytest.raises(HTTPException) as error:
            await invites_service.accept_invite("token", "New User", "secret")

    assert error.value.status_code == 409
    assert error.value.detail == "Email already registered"


async def test_accept_invite_returns_conflict_for_integrity_error() -> None:
    invite = build_invite_details()

    with (
        patch.object(
            invites_service.queries,
            "get_invite_by_token_hash",
            AsyncMock(return_value=invite),
        ),
        patch(
            "src.services.invites.get_user_by_email",
            AsyncMock(return_value=None),
        ),
        patch.object(
            invites_service.queries,
            "accept_invite_and_create_user",
            AsyncMock(side_effect=IntegrityError("insert", {}, Exception("duplicate"))),
        ),
    ):
        with pytest.raises(HTTPException) as error:
            await invites_service.accept_invite("token", "New User", "secret")

    assert error.value.status_code == 409
    assert error.value.detail == "Email already registered"
