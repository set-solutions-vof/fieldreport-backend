from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.exceptions import InviteAlreadyExists
from src.models.onboarding import (
    CompanyOnboarding,
    CompanyOnboardingUpdate,
    InviteCreated,
    InviteRecord,
)
from src.services import onboarding as onboarding_service


async def test_get_company_returns_company() -> None:
    company = CompanyOnboarding(
        id=uuid4(),
        name="LEKK BV",
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
        name="LEKK BV",
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
    invite = InviteCreated(
        id=uuid4(),
        email="new.user@lekk.nl",
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
            "create_invite",
            AsyncMock(return_value=invite),
        ) as create_invite,
        patch.object(onboarding_service.secrets, "token_hex", return_value="token"),
    ):
        result = await onboarding_service.create_invite(
            company_id,
            "new.user@lekk.nl",
            "admin",
        )

    assert result == invite
    assert create_invite.await_args.args[0] == company_id
    assert create_invite.await_args.args[1:3] == ("new.user@lekk.nl", "admin")
    assert create_invite.await_args.args[3] == "token"


async def test_create_invite_raises_when_pending_invite_exists() -> None:
    with patch.object(
        onboarding_service.onboarding_queries,
        "has_pending_invite",
        AsyncMock(return_value=True),
    ):
        with pytest.raises(InviteAlreadyExists):
            await onboarding_service.create_invite(
                str(uuid4()),
                "new.user@lekk.nl",
                "inspector",
            )


async def test_list_invites_returns_invites() -> None:
    invite = InviteRecord(
        id=uuid4(),
        email="new.user@lekk.nl",
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
