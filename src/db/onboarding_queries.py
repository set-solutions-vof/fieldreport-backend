from datetime import datetime
from uuid import uuid4

from src.db.connection import get_pool
from src.db.onboarding_mapper import (
    map_company,
    map_created_invite,
    map_invite,
    map_invite_details,
)
from src.models.onboarding.company import CompanyOnboarding
from src.models.onboarding.invite import InviteCreated, InviteRecord
from src.models.onboarding.invite_details import InviteDetails


async def get_company(company_id: str) -> CompanyOnboarding:
    async with get_pool().acquire() as connection:
        row = await connection.fetchrow(
            """
            SELECT
                id,
                name,
                logo_url,
                primary_color,
                onboarding_completed
            FROM company
            WHERE id = $1::uuid
            """,
            company_id,
        )

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
    async with get_pool().acquire() as connection:
        row = await connection.fetchrow(
            """
            UPDATE company
            SET
                logo_url = CASE WHEN $2::boolean THEN $3::text ELSE logo_url END,
                primary_color = CASE WHEN $4::boolean THEN $5::varchar(7) ELSE primary_color END,
                onboarding_completed = CASE
                    WHEN $6::boolean THEN $7::boolean
                    ELSE onboarding_completed
                END
            WHERE id = $1::uuid
            RETURNING
                id,
                name,
                logo_url,
                primary_color,
                onboarding_completed
            """,
            company_id,
            should_update_logo_url,
            logo_url,
            should_update_primary_color,
            primary_color,
            should_update_onboarding_completed,
            onboarding_completed,
        )

    return map_company(row)


async def has_pending_invite(company_id: str, email: str) -> bool:
    async with get_pool().acquire() as connection:
        row = await connection.fetchrow(
            """
            SELECT id
            FROM invites
            WHERE company_id = $1::uuid
            AND email = $2::text
            AND is_accepted = false
            """,
            company_id,
            email,
        )

    return row is not None


async def create_invite(
    company_id: str,
    email: str,
    role: str,
    token: str,
    expires_at: datetime,
) -> InviteCreated:
    async with get_pool().acquire() as connection:
        row = await connection.fetchrow(
            """
            INSERT INTO invites (
                id,
                company_id,
                email,
                role,
                token,
                is_accepted,
                expires_at,
                created_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                $3::text,
                $4::user_role,
                $5::text,
                false,
                $6::timestamptz,
                NOW()
            )
            RETURNING
                id,
                email,
                role,
                created_at
            """,
            str(uuid4()),
            company_id,
            email,
            role,
            token,
            expires_at,
        )

    return map_created_invite(row)


async def list_invites(company_id: str) -> list[InviteRecord]:
    async with get_pool().acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT
                id,
                email,
                role,
                is_accepted,
                created_at,
                expires_at
            FROM invites
            WHERE company_id = $1::uuid
            ORDER BY created_at DESC
            """,
            company_id,
        )

    return [map_invite(row) for row in rows]


async def get_invite_by_token_hash(token_hash: str) -> InviteDetails | None:
    async with get_pool().acquire() as connection:
        row = await connection.fetchrow(
            """
            SELECT
                invites.id,
                invites.company_id,
                company.name AS company_name,
                invites.email,
                invites.role,
                invites.is_accepted,
                invites.expires_at
            FROM invites
            JOIN company ON company.id = invites.company_id
            WHERE invites.token = $1::text
            """,
            token_hash,
        )

    if row is None:
        return None

    return map_invite_details(row)


async def accept_invite_and_create_user(
    invite_id: str,
    company_id: str,
    email: str,
    name: str,
    role: str,
    password_hash: str,
) -> str:
    async with get_pool().acquire() as connection:
        async with connection.transaction():
            invite_row = await connection.fetchrow(
                """
                SELECT id
                FROM invites
                WHERE id = $1::uuid
                AND company_id = $2::uuid
                AND email = $3::text
                AND is_accepted = false
                AND expires_at > NOW()
                FOR UPDATE
                """,
                invite_id,
                company_id,
                email,
            )

            if invite_row is None:
                return ""

            user_row = await connection.fetchrow(
                """
                INSERT INTO users (
                    id,
                    company_id,
                    email,
                    password_hash,
                    name,
                    phone_number,
                    role,
                    created_at
                )
                VALUES (
                    $1::uuid,
                    $2::uuid,
                    $3::text,
                    $4::text,
                    $5::text,
                    '',
                    $6::user_role,
                    NOW()
                )
                RETURNING id
                """,
                str(uuid4()),
                company_id,
                email,
                password_hash,
                name,
                role,
            )

            await connection.execute(
                """
                UPDATE invites
                SET is_accepted = true
                WHERE id = $1::uuid
                """,
                invite_id,
            )

    return str(user_row["id"])


async def delete_pending_invite(company_id: str, invite_id: str) -> bool:
    async with get_pool().acquire() as connection:
        row = await connection.fetchrow(
            """
            DELETE FROM invites
            WHERE id = $1::uuid
            AND company_id = $2::uuid
            AND is_accepted = false
            RETURNING id
            """,
            invite_id,
            company_id,
        )

    return row is not None
