from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.models.enums.user_role import UserRole


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


class InviteRecord(BaseModel):
    id: UUID
    email: str
    role: UserRole
    created_at: datetime
    expires_at: datetime
    is_accepted: bool


class InviteCreated(BaseModel):
    id: UUID
    email: str
    role: UserRole
    created_at: datetime
