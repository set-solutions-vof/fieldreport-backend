import asyncpg

from src.http.v1.response.onboarding import (
    CompanyOnboardingResponse,
    InviteCreatedResponse,
    InviteResponse,
)


def map_company(row: asyncpg.Record) -> CompanyOnboardingResponse:
    return CompanyOnboardingResponse.model_validate(dict(row))


def map_created_invite(row: asyncpg.Record) -> InviteCreatedResponse:
    return InviteCreatedResponse.model_validate(dict(row))


def map_invite(row: asyncpg.Record) -> InviteResponse:
    return InviteResponse.model_validate(dict(row))
