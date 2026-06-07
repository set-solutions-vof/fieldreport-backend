import secrets
from datetime import UTC, datetime, timedelta

from src.config import settings
from src.db import onboarding_queries
from src.email.invite_email import send_invite_email
from src.exceptions import InviteAlreadyExists, InviteEmailDeliveryFailed
from src.models.enums.user_role import UserRole
from src.models.onboarding.company import CompanyOnboarding, CompanyOnboardingUpdate
from src.models.onboarding.invite import InviteCreated, InviteRecord
from src.security.invite_tokens import hash_invite_token


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

    if not _smtp_is_configured():
        raise InviteEmailDeliveryFailed()

    raw_token = secrets.token_hex(32)
    token_hash = hash_invite_token(raw_token)
    expires_at = datetime.now(UTC) + timedelta(days=7)
    company = await onboarding_queries.get_company(company_id)
    invite = await onboarding_queries.create_invite(
        company_id,
        email,
        role,
        token_hash,
        expires_at,
    )

    try:
        await send_invite_email(
            to_email=email,
            company_name=company.name,
            role=role,
            token=raw_token,
        )
    except Exception as error:
        await onboarding_queries.delete_pending_invite(company_id, str(invite.id))
        raise InviteEmailDeliveryFailed() from error

    return invite


def _smtp_is_configured() -> bool:
    return all(
        [
            settings.smtp_host,
            settings.smtp_username,
            settings.smtp_password,
            settings.smtp_from_email,
        ]
    )


async def list_invites(company_id: str) -> list[InviteRecord]:
    return await onboarding_queries.list_invites(company_id)


async def delete_pending_invite(company_id: str, invite_id: str) -> bool:
    return await onboarding_queries.delete_pending_invite(company_id, invite_id)
