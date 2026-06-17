from src.db.onboarding import queries
from src.models.onboarding.company import CompanyOnboarding, CompanyOnboardingUpdate


async def get_company(company_id: str) -> CompanyOnboarding:
    return await queries.get_company(company_id)


async def update_company(
    company_id: str,
    update: CompanyOnboardingUpdate,
) -> CompanyOnboarding:
    return await queries.update_company(
        company_id,
        update.logo_url,
        update.primary_color,
        update.onboarding_completed,
        update.update_logo_url,
        update.update_primary_color,
        update.update_onboarding_completed,
    )
