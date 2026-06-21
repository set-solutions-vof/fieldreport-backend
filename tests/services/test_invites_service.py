from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from asyncpg import UniqueViolationError
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.exceptions import InviteAlreadyExists, InviteEmailDeliveryFailed, InviteInvalid
from src.models.auth.authentication import CurrentUser
from src.models.onboarding.company import CompanyOnboarding
from src.models.onboarding.invite import InviteCreated, InviteRecord
from src.models.onboarding.invite_details import InviteDetails
from src.models.onboarding.invite_preview import InvitePreview
from src.security.invite_tokens import hash_invite_token
from src.services import invites as invites_service


def build_invite_details(*, is_accepted: bool = False) -> InviteDetails:
    return InviteDetails(
        id=uuid4(),
        company_id=uuid4(),
        company_name="Demo Company",
        first_name="New",
        last_name="User",
        email="new.user@example.com",
        role="inspector",
        is_accepted=is_accepted,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )


async def test_create_invite_returns_created_invite_and_delivery() -> None:
    company_id = str(uuid4())
    created_at = datetime.now(UTC)
    expires_at = created_at + timedelta(days=7)
    company = CompanyOnboarding(
        id=uuid4(),
        name="Demo Company",
        logo_url=None,
        primary_color=None,
        onboarding_completed=True,
    )
    invite = InviteCreated(
        id=uuid4(),
        first_name="New",
        last_name="User",
        email="new.user@example.com",
        role="admin",
        created_at=created_at,
        expires_at=expires_at,
    )

    with (
        patch.object(
            invites_service.queries,
            "has_pending_invite",
            AsyncMock(return_value=False),
        ),
        patch.object(
            invites_service.queries,
            "get_company",
            AsyncMock(return_value=company),
        ),
        patch.object(
            invites_service.queries,
            "create_invite",
            AsyncMock(return_value=invite),
        ) as create_invite,
        patch.object(invites_service, "_smtp_is_configured", return_value=True),
        patch.object(invites_service, "send_invite_email", AsyncMock()) as send_email,
        patch.object(invites_service.secrets, "token_hex", return_value="raw-token"),
    ):
        created_invite, delivery = await invites_service.create_invite(
            company_id,
            "new.user@example.com",
            "admin",
        )

    assert created_invite == invite
    assert delivery == invites_service.InviteEmailDelivery(
        company_id=company_id,
        invite_id=str(invite.id),
        to_email="new.user@example.com",
        company_name="Demo Company",
        role="admin",
        token="raw-token",
    )
    assert create_invite.await_args.args[0] == company_id
    assert create_invite.await_args.args[1:3] == ("new.user@example.com", "admin")
    assert create_invite.await_args.args[3] == hash_invite_token("raw-token")
    send_email.assert_not_awaited()


def test_smtp_is_configured_returns_false_when_from_email_is_missing() -> None:
    with (
        patch.object(invites_service.settings, "smtp_host", "smtp.office365.com"),
        patch.object(invites_service.settings, "smtp_username", "smtp-user"),
        patch.object(invites_service.settings, "smtp_password", "smtp-pass"),
        patch.object(invites_service.settings, "smtp_from_email", ""),
    ):
        assert invites_service._smtp_is_configured() is False


async def test_create_invite_raises_when_smtp_is_not_configured() -> None:
    with (
        patch.object(
            invites_service.queries,
            "has_pending_invite",
            AsyncMock(return_value=False),
        ),
        patch.object(invites_service, "_smtp_is_configured", return_value=False),
    ):
        with pytest.raises(InviteEmailDeliveryFailed):
            await invites_service.create_invite(
                str(uuid4()),
                "new.user@example.com",
                "admin",
            )


async def test_deliver_invite_email_sends_message() -> None:
    delivery = invites_service.InviteEmailDelivery(
        company_id=str(uuid4()),
        invite_id=str(uuid4()),
        to_email="new.user@example.com",
        company_name="Demo Company",
        role="admin",
        token="raw-token",
    )

    with patch.object(
        invites_service,
        "send_invite_email",
        AsyncMock(),
    ) as send_email:
        await invites_service.deliver_invite_email(delivery)

    send_email.assert_awaited_once_with(
        to_email="new.user@example.com",
        company_name="Demo Company",
        role="admin",
        token="raw-token",
    )


async def test_deliver_invite_email_deletes_pending_invite_when_send_fails() -> None:
    company_id = str(uuid4())
    invite_id = str(uuid4())
    delivery = invites_service.InviteEmailDelivery(
        company_id=company_id,
        invite_id=invite_id,
        to_email="new.user@example.com",
        company_name="Demo Company",
        role="admin",
        token="raw-token",
    )

    with (
        patch.object(
            invites_service,
            "send_invite_email",
            AsyncMock(side_effect=RuntimeError("smtp failed")),
        ),
        patch.object(
            invites_service.queries,
            "delete_pending_invite",
            AsyncMock(),
        ) as delete_pending_invite,
    ):
        await invites_service.deliver_invite_email(delivery)

    delete_pending_invite.assert_awaited_once_with(company_id, invite_id)


async def test_create_invite_raises_when_pending_invite_exists() -> None:
    with patch.object(
        invites_service.queries,
        "has_pending_invite",
        AsyncMock(return_value=True),
    ):
        with pytest.raises(InviteAlreadyExists):
            await invites_service.create_invite(
                str(uuid4()),
                "new.user@example.com",
                "inspector",
            )


async def test_list_invites_returns_invites() -> None:
    invite = InviteRecord(
        id=uuid4(),
        first_name="New",
        last_name="User",
        email="new.user@example.com",
        role="inspector",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
        is_accepted=False,
    )

    with patch.object(
        invites_service.queries,
        "list_invites",
        AsyncMock(return_value=[invite]),
    ):
        result = await invites_service.list_invites(str(uuid4()))

    assert result == [invite]


async def test_delete_pending_invite_returns_repository_result() -> None:
    with patch.object(
        invites_service.queries,
        "delete_pending_invite",
        AsyncMock(return_value=True),
    ):
        result = await invites_service.delete_pending_invite(str(uuid4()), str(uuid4()))

    assert result is True


async def test_get_invite_preview_returns_preview() -> None:
    invite = build_invite_details()

    with patch.object(
        invites_service.queries,
        "get_invite_by_token_hash",
        AsyncMock(return_value=invite),
    ):
        result = await invites_service.get_invite_preview("token")

    assert result == InvitePreview(
        first_name="New",
        last_name="User",
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
        first_name="New",
        last_name="User",
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
        result = await invites_service.accept_invite("token", "secret")

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
        first_name="Existing",
        last_name="User",
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
            await invites_service.accept_invite("token", "secret")


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
            await invites_service.accept_invite("token", "secret")


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
            await invites_service.accept_invite("token", "secret")


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
            await invites_service.accept_invite("token", "secret")

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
            await invites_service.accept_invite("token", "secret")

    assert error.value.status_code == 409
    assert error.value.detail == "Email already registered"
