from pydantic import BaseModel

from src.models.enums.user_role import UserRole


class UpdateCompanyOnboardingRequest(BaseModel):
    logo_url: str | None = None
    primary_color: str | None = None
    onboarding_completed: bool | None = None


class CreateInviteRequest(BaseModel):
    email: str
    role: UserRole
