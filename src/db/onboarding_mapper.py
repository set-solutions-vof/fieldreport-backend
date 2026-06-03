import asyncpg

from src.models.onboarding.company import CompanyOnboarding
from src.models.onboarding.invite import InviteCreated, InviteRecord


def map_company(row: asyncpg.Record) -> CompanyOnboarding:
    return CompanyOnboarding.model_validate(dict(row))


def map_created_invite(row: asyncpg.Record) -> InviteCreated:
    return InviteCreated.model_validate(dict(row))


def map_invite(row: asyncpg.Record) -> InviteRecord:
    return InviteRecord.model_validate(dict(row))
