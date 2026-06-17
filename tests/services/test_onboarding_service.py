from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.models.onboarding.company import CompanyOnboarding, CompanyOnboardingUpdate
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
        onboarding_service.queries,
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
        onboarding_service.queries,
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
