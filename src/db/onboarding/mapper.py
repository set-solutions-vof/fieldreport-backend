from collections.abc import Mapping

from src.models.onboarding.company import CompanyOnboarding
from src.models.onboarding.invite import InviteCreated, InviteRecord
from src.models.onboarding.invite_details import InviteDetails


def map_company(row: Mapping[str, object]) -> CompanyOnboarding:
    return CompanyOnboarding.model_validate(dict(row))


def map_created_invite(row: Mapping[str, object]) -> InviteCreated:
    return InviteCreated.model_validate(dict(row))


def map_invite(row: Mapping[str, object]) -> InviteRecord:
    return InviteRecord.model_validate(dict(row))


def map_invite_details(row: Mapping[str, object]) -> InviteDetails:
    return InviteDetails.model_validate(dict(row))
