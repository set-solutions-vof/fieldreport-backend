from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.models.enums.user_role import UserRole


class CompanyOnboardingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    logo_url: str | None
    primary_color: str | None
    onboarding_completed: bool


class InviteCreatedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: UserRole
    created_at: datetime


class InviteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: UserRole
    is_accepted: bool
    created_at: datetime
    expires_at: datetime
