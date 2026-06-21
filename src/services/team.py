from src.db.onboarding import queries as onboarding_queries
from src.db.team import queries
from src.models.enums.user_role import UserRole
from src.models.onboarding.invite import InviteCreated, InviteRecord
from src.models.team.user import TeamUser
from src.services import invites as invites_service
from src.services.invites import InviteEmailDelivery


async def list_team_users(company_id: str) -> list[TeamUser]:
    members = await queries.list_company_members(company_id)
    pending_invites = [
        invite
        for invite in await onboarding_queries.list_invites(company_id)
        if not invite.is_accepted
    ]

    users = [_member_to_team_user(member) for member in members]
    users.extend(_invite_to_team_user(invite) for invite in pending_invites)

    return sorted(
        users,
        key=lambda user: f"{user.last_name} {user.first_name}".casefold(),
    )


async def create_team_user(
    company_id: str,
    first_name: str,
    last_name: str,
    email: str,
    role: UserRole,
) -> tuple[TeamUser, InviteEmailDelivery]:
    invite, delivery = await invites_service.create_invite(
        company_id,
        email,
        role,
        first_name,
        last_name,
    )

    return _invite_to_team_user(invite), delivery


async def get_team_user(company_id: str, user_id: str) -> TeamUser | None:
    member = await queries.get_company_member(company_id, user_id)

    if member is not None:
        return _member_to_team_user(member)

    invite = await onboarding_queries.get_pending_invite(company_id, user_id)

    if invite is None:
        return None

    return _invite_to_team_user(invite)


async def update_team_user(
    company_id: str,
    user_id: str,
    first_name: str,
    last_name: str,
    role: UserRole,
) -> TeamUser | None:
    member = await queries.update_company_member(
        company_id,
        user_id,
        first_name,
        last_name,
        role,
    )

    if member is not None:
        return _member_to_team_user(member)

    invite = await onboarding_queries.update_pending_invite(
        company_id,
        user_id,
        first_name,
        last_name,
        role,
    )

    if invite is None:
        return None

    return _invite_to_team_user(invite)


async def delete_team_user(company_id: str, user_id: str) -> bool:
    if await queries.delete_company_member(company_id, user_id):
        return True

    return await onboarding_queries.delete_pending_invite(company_id, user_id)


def _member_to_team_user(member) -> TeamUser:
    return TeamUser(
        id=member.id,
        first_name=member.first_name,
        last_name=member.last_name,
        email=member.email,
        role=member.role,
        status="active",
        created_at=member.created_at,
        last_sign_in_at=member.last_sign_in_at,
    )


def _invite_to_team_user(invite: InviteCreated | InviteRecord) -> TeamUser:
    return TeamUser(
        id=invite.id,
        first_name=invite.first_name,
        last_name=invite.last_name,
        email=invite.email,
        role=invite.role,
        status="invited",
        created_at=invite.created_at,
        last_sign_in_at=None,
    )
