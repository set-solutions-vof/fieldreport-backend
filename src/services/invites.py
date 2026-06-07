from datetime import UTC, datetime

from src.db import auth_queries, onboarding_queries
from src.exceptions import InviteInvalid
from src.models.auth.authentication import TokenPair
from src.models.onboarding.invite_details import InviteDetails
from src.models.onboarding.invite_preview import InvitePreview
from src.security import authentication
from src.security.invite_tokens import hash_invite_token


async def _get_valid_invite(token: str) -> InviteDetails:
    invite = await onboarding_queries.get_invite_by_token_hash(hash_invite_token(token))

    if invite is None or invite.is_accepted or invite.expires_at <= datetime.now(UTC):
        raise InviteInvalid()

    return invite


async def get_invite_preview(token: str) -> InvitePreview:
    invite = await _get_valid_invite(token)

    return InvitePreview(
        email=invite.email,
        role=invite.role,
        company_name=invite.company_name,
    )


async def accept_invite(token: str, name: str, password: str) -> TokenPair:
    invite = await _get_valid_invite(token)

    existing_user = await auth_queries.get_user_by_email(invite.email)

    if existing_user is not None:
        raise InviteInvalid()

    user_id = await onboarding_queries.accept_invite_and_create_user(
        str(invite.id),
        str(invite.company_id),
        invite.email,
        name,
        invite.role,
        authentication.hash_password(password),
    )

    if user_id == "":
        raise InviteInvalid()

    current_user = await auth_queries.get_user_by_id(user_id)

    if current_user is None:
        raise InviteInvalid()

    return TokenPair(
        access_token=authentication.create_access_token(current_user),
        refresh_token=authentication.create_refresh_token(current_user),
        token_type="bearer",
    )
