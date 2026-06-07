from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.exceptions import InviteAlreadyExists, InviteEmailDeliveryFailed
from src.models.onboarding.company import CompanyOnboarding, CompanyOnboardingUpdate
from src.models.onboarding.invite import InviteCreated, InviteRecord
from src.security.invite_tokens import hash_invite_token
from src.services import onboarding as onboarding_service


async def test_get_company_returns_company() -> None:
    company = CompanyOnboarding(
        id=uuid4(),
        name="Demo Company",
        logo_url=None,
        primary_color="#3B5BDB",
        onboarding_completed=False,
    )

    with patch.object(
        onboarding_service.onboarding_queries,
        "get_company",
        AsyncMock(return_value=company),
    ):
        result = await onboarding_service.get_company(str(company.id))

    assert result == company


async def test_update_company_returns_updated_company() -> None:
    company = CompanyOnboarding(
        id=uuid4(),
        name="Demo Company",
        logo_url="https://cdn.example/logo.png",
        primary_color="#3B5BDB",
        onboarding_completed=True,
    )
    update = CompanyOnboardingUpdate(
        logo_url="https://cdn.example/logo.png",
        primary_color="#3B5BDB",
        onboarding_completed=True,
        update_logo_url=True,
        update_primary_color=True,
        update_onboarding_completed=True,
    )

    with patch.object(
        onboarding_service.onboarding_queries,
        "update_company",
        AsyncMock(return_value=company),
    ) as update_company:
        result = await onboarding_service.update_company(str(company.id), update)

    assert result == company
    update_company.assert_awaited_once_with(
        str(company.id),
        update.logo_url,
        update.primary_color,
        update.onboarding_completed,
        update.update_logo_url,
        update.update_primary_color,
        update.update_onboarding_completed,
    )


async def test_create_invite_returns_created_invite() -> None:
    company_id = str(uuid4())
    created_at = datetime.now(UTC)
    company = CompanyOnboarding(
        id=uuid4(),
        name="Demo Company",
        logo_url=None,
        primary_color=None,
        onboarding_completed=True,
    )
    invite = InviteCreated(
        id=uuid4(),
        email="new.user@example.com",
        role="admin",
        created_at=created_at,
    )

    with (
        patch.object(
            onboarding_service.onboarding_queries,
            "has_pending_invite",
            AsyncMock(return_value=False),
        ),
        patch.object(
            onboarding_service.onboarding_queries,
            "get_company",
            AsyncMock(return_value=company),
        ),
        patch.object(
            onboarding_service.onboarding_queries,
            "create_invite",
            AsyncMock(return_value=invite),
        ) as create_invite,
        patch.object(onboarding_service, "_smtp_is_configured", return_value=True),
        patch.object(onboarding_service, "send_invite_email", AsyncMock()) as send_email,
        patch.object(onboarding_service.secrets, "token_hex", return_value="raw-token"),
    ):
        result = await onboarding_service.create_invite(
            company_id,
            "new.user@example.com",
            "admin",
        )

    assert result == invite
    assert create_invite.await_args.args[0] == company_id
    assert create_invite.await_args.args[1:3] == ("new.user@example.com", "admin")
    assert create_invite.await_args.args[3] == hash_invite_token("raw-token")
    send_email.assert_awaited_once()


def test_smtp_is_configured_returns_false_when_from_email_is_missing() -> None:
    with (
        patch.object(onboarding_service.settings, "smtp_host", "smtp.office365.com"),
        patch.object(onboarding_service.settings, "smtp_username", "smtp-user"),
        patch.object(onboarding_service.settings, "smtp_password", "smtp-pass"),
        patch.object(onboarding_service.settings, "smtp_from_email", ""),
    ):
        assert onboarding_service._smtp_is_configured() is False


async def test_create_invite_raises_when_smtp_is_not_configured() -> None:
    with (
        patch.object(
            onboarding_service.onboarding_queries,
            "has_pending_invite",
            AsyncMock(return_value=False),
        ),
        patch.object(onboarding_service, "_smtp_is_configured", return_value=False),
    ):
        with pytest.raises(InviteEmailDeliveryFailed):
            await onboarding_service.create_invite(
                str(uuid4()),
                "new.user@example.com",
                "admin",
            )


async def test_create_invite_deletes_pending_invite_when_email_send_fails() -> None:
    company_id = str(uuid4())
    created_at = datetime.now(UTC)
    company = CompanyOnboarding(
        id=uuid4(),
        name="Demo Company",
        logo_url=None,
        primary_color=None,
        onboarding_completed=True,
    )
    invite = InviteCreated(
        id=uuid4(),
        email="new.user@example.com",
        role="admin",
        created_at=created_at,
    )

    with (
        patch.object(
            onboarding_service.onboarding_queries,
            "has_pending_invite",
            AsyncMock(return_value=False),
        ),
        patch.object(
            onboarding_service.onboarding_queries,
            "get_company",
            AsyncMock(return_value=company),
        ),
        patch.object(
            onboarding_service.onboarding_queries,
            "create_invite",
            AsyncMock(return_value=invite),
        ),
        patch.object(onboarding_service, "_smtp_is_configured", return_value=True),
        patch.object(
            onboarding_service,
            "send_invite_email",
            AsyncMock(side_effect=RuntimeError("smtp failed")),
        ),
        patch.object(
            onboarding_service.onboarding_queries,
            "delete_pending_invite",
            AsyncMock(),
        ) as delete_pending_invite,
        patch.object(onboarding_service.secrets, "token_hex", return_value="raw-token"),
    ):
        with pytest.raises(InviteEmailDeliveryFailed):
            await onboarding_service.create_invite(
                company_id,
                "new.user@example.com",
                "admin",
            )

    delete_pending_invite.assert_awaited_once_with(company_id, str(invite.id))


async def test_create_invite_raises_when_pending_invite_exists() -> None:
    with patch.object(
        onboarding_service.onboarding_queries,
        "has_pending_invite",
        AsyncMock(return_value=True),
    ):
        with pytest.raises(InviteAlreadyExists):
            await onboarding_service.create_invite(
                str(uuid4()),
                "new.user@example.com",
                "inspector",
            )


async def test_list_invites_returns_invites() -> None:
    invite = InviteRecord(
        id=uuid4(),
        email="new.user@example.com",
        role="inspector",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
        is_accepted=False,
    )

    with patch.object(
        onboarding_service.onboarding_queries,
        "list_invites",
        AsyncMock(return_value=[invite]),
    ):
        result = await onboarding_service.list_invites(str(uuid4()))

    assert result == [invite]


async def test_delete_pending_invite_returns_repository_result() -> None:
    with patch.object(
        onboarding_service.onboarding_queries,
        "delete_pending_invite",
        AsyncMock(return_value=True),
    ):
        result = await onboarding_service.delete_pending_invite(str(uuid4()), str(uuid4()))

    assert result is True
