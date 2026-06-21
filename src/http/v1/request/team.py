from pydantic import BaseModel, EmailStr

from src.models.enums.user_role import UserRole


class CreateTeamUserRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    role: UserRole


class UpdateTeamUserRequest(BaseModel):
    first_name: str
    last_name: str
    role: UserRole
