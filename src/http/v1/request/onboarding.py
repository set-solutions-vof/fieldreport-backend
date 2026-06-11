from pydantic import BaseModel, EmailStr

from src.models.enums.user_role import UserRole


class UpdateCompanyOnboardingRequest(BaseModel):
    logo_url: str | None = None
    primary_color: str | None = None
    onboarding_completed: bool | None = None


class CreateInviteRequest(BaseModel):
    email: EmailStr
    role: UserRole
