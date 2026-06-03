import secrets
from datetime import UTC, datetime, timedelta

from src.db import onboarding_queries
from src.exceptions import InviteAlreadyExists
from src.models.enums.user_role import UserRole
from src.models.onboarding.company import CompanyOnboarding, CompanyOnboardingUpdate
from src.models.onboarding.invite import InviteCreated, InviteRecord


async def get_company(company_id: str) -> CompanyOnboarding:
    return await onboarding_queries.get_company(company_id)


async def update_company(
    company_id: str,
    update: CompanyOnboardingUpdate,
) -> CompanyOnboarding:
    return await onboarding_queries.update_company(
        company_id,
        update.logo_url,
        update.primary_color,
        update.onboarding_completed,
        update.update_logo_url,
        update.update_primary_color,
        update.update_onboarding_completed,
    )


async def create_invite(
    company_id: str,
    email: str,
    role: UserRole,
) -> InviteCreated:
    if await onboarding_queries.has_pending_invite(company_id, email):
        raise InviteAlreadyExists(email)

    token = secrets.token_hex(32)
    expires_at = datetime.now(UTC) + timedelta(days=7)

    return await onboarding_queries.create_invite(company_id, email, role, token, expires_at)


async def list_invites(company_id: str) -> list[InviteRecord]:
    return await onboarding_queries.list_invites(company_id)


async def delete_pending_invite(company_id: str, invite_id: str) -> bool:
    return await onboarding_queries.delete_pending_invite(company_id, invite_id)
