from pydantic import BaseModel

from src.models.enums.user_role import UserRole


class InvitePreview(BaseModel):
    first_name: str
    last_name: str
    email: str
    role: UserRole
    company_name: str
