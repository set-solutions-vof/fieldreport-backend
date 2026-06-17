from uuid import UUID

from pydantic import BaseModel


class CompanyOnboarding(BaseModel):
    id: UUID
    name: str
    logo_url: str | None
    primary_color: str | None
    onboarding_completed: bool


class CompanyOnboardingUpdate(BaseModel):
    logo_url: str | None = None
    primary_color: str | None = None
    onboarding_completed: bool | None = None
    update_logo_url: bool
    update_primary_color: bool
    update_onboarding_completed: bool
