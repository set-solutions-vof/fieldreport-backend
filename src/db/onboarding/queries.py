from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa

from src.db.connection import get_database
from src.db.onboarding.mapper import (
    map_company,
    map_created_invite,
    map_invite,
    map_invite_details,
)
from src.db.schema.tables import company, invites, users
from src.models.onboarding.company import CompanyOnboarding
from src.models.onboarding.invite import InviteCreated, InviteRecord
from src.models.onboarding.invite_details import InviteDetails


def _company_columns():
    return (
        company.c.id,
        company.c.name,
        company.c.logo_url,
        company.c.primary_color,
        company.c.onboarding_completed,
    )


async def get_company(company_id: str) -> CompanyOnboarding:
    statement = sa.select(*_company_columns()).where(company.c.id == company_id)

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().one()

    return map_company(row)


async def update_company(
    company_id: str,
    logo_url: str | None,
    primary_color: str | None,
    onboarding_completed: bool | None,
    should_update_logo_url: bool,
    should_update_primary_color: bool,
    should_update_onboarding_completed: bool,
) -> CompanyOnboarding:
    statement = (
        company.update()
        .where(company.c.id == company_id)
        .values(
            logo_url=sa.case(
                (sa.literal(should_update_logo_url), logo_url),
                else_=company.c.logo_url,
            ),
            primary_color=sa.case(
                (sa.literal(should_update_primary_color), primary_color),
                else_=company.c.primary_color,
            ),
            onboarding_completed=sa.case(
                (sa.literal(should_update_onboarding_completed), onboarding_completed),
                else_=company.c.onboarding_completed,
            ),
        )
        .returning(*_company_columns())
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().one()

    return map_company(row)


async def has_pending_invite(company_id: str, email: str) -> bool:
    statement = sa.select(invites.c.id).where(
        invites.c.company_id == company_id,
        invites.c.email == email,
        invites.c.is_accepted.is_(False),
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().first()

    return row is not None


async def create_invite(
    company_id: str,
    email: str,
    role: str,
    token: str,
    expires_at: datetime,
    first_name: str,
    last_name: str,
) -> InviteCreated:
    statement = (
        invites.insert()
        .values(
            id=str(uuid4()),
            company_id=company_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            token=token,
            is_accepted=False,
            expires_at=expires_at,
            created_at=sa.func.now(),
        )
        .returning(
            invites.c.id,
            invites.c.first_name,
            invites.c.last_name,
            invites.c.email,
            invites.c.role,
            invites.c.created_at,
            invites.c.expires_at,
        )
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().one()

    return map_created_invite(row)


async def list_invites(company_id: str) -> list[InviteRecord]:
    statement = (
        sa.select(
            invites.c.id,
            invites.c.first_name,
            invites.c.last_name,
            invites.c.email,
            invites.c.role,
            invites.c.is_accepted,
            invites.c.created_at,
            invites.c.expires_at,
        )
        .where(invites.c.company_id == company_id)
        .order_by(invites.c.created_at.desc())
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        rows = result.mappings().all()

    return [map_invite(row) for row in rows]


async def get_invite_by_token_hash(token_hash: str) -> InviteDetails | None:
    statement = (
        sa.select(
            invites.c.id,
            invites.c.company_id,
            company.c.name.label("company_name"),
            invites.c.first_name,
            invites.c.last_name,
            invites.c.email,
            invites.c.role,
            invites.c.is_accepted,
            invites.c.expires_at,
        )
        .select_from(invites.join(company, company.c.id == invites.c.company_id))
        .where(invites.c.token == token_hash)
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().first()

    if row is None:
        return None

    return map_invite_details(row)


async def accept_invite_and_create_user(
    invite_id: str,
    company_id: str,
    email: str,
    first_name: str,
    last_name: str,
    role: str,
    password_hash: str,
) -> str:
    async with get_database().acquire() as connection:
        async with connection.transaction():
            invite_statement = (
                sa.select(invites.c.id)
                .where(
                    invites.c.id == invite_id,
                    invites.c.company_id == company_id,
                    invites.c.email == email,
                    invites.c.is_accepted.is_(False),
                    invites.c.expires_at > sa.func.now(),
                )
                .with_for_update()
            )
            invite_result = await connection.execute(invite_statement)
            invite_row = invite_result.mappings().first()

            if invite_row is None:
                return ""

            user_statement = (
                users.insert()
                .values(
                    id=str(uuid4()),
                    company_id=company_id,
                    email=email,
                    password_hash=password_hash,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number="",
                    role=role,
                    created_at=sa.func.now(),
                )
                .returning(users.c.id)
            )
            user_result = await connection.execute(user_statement)
            user_row = user_result.mappings().one()

            update_statement = (
                invites.update().where(invites.c.id == invite_id).values(is_accepted=True)
            )
            await connection.execute(update_statement)

    return str(user_row["id"])


async def delete_pending_invite(company_id: str, invite_id: str) -> bool:
    statement = (
        invites.delete()
        .where(
            invites.c.id == invite_id,
            invites.c.company_id == company_id,
            invites.c.is_accepted.is_(False),
        )
        .returning(invites.c.id)
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().first()

    return row is not None


async def get_pending_invite(company_id: str, invite_id: str) -> InviteRecord | None:
    statement = sa.select(
        invites.c.id,
        invites.c.first_name,
        invites.c.last_name,
        invites.c.email,
        invites.c.role,
        invites.c.is_accepted,
        invites.c.created_at,
        invites.c.expires_at,
    ).where(
        invites.c.id == invite_id,
        invites.c.company_id == company_id,
        invites.c.is_accepted.is_(False),
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().first()

    if row is None:
        return None

    return map_invite(row)


async def update_pending_invite(
    company_id: str,
    invite_id: str,
    first_name: str,
    last_name: str,
    role: str,
) -> InviteRecord | None:
    statement = (
        invites.update()
        .where(
            invites.c.id == invite_id,
            invites.c.company_id == company_id,
            invites.c.is_accepted.is_(False),
        )
        .values(
            first_name=first_name,
            last_name=last_name,
            role=role,
        )
        .returning(
            invites.c.id,
            invites.c.first_name,
            invites.c.last_name,
            invites.c.email,
            invites.c.role,
            invites.c.is_accepted,
            invites.c.created_at,
            invites.c.expires_at,
        )
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().first()

    if row is None:
        return None

    return map_invite(row)
