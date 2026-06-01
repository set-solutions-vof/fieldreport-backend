from uuid import UUID

from pydantic import BaseModel

from src.models.enums.token_type import TokenType
from src.models.enums.user_role import UserRole


class LoginCredentials(BaseModel):
    email: str
    password: str


class AuthenticatedUser(BaseModel):
    id: UUID
    company_id: UUID
    company_name: str
    email: str
    password_hash: str
    name: str
    role: UserRole


class CurrentUser(BaseModel):
    id: UUID
    company_id: UUID
    company_name: str
    email: str
    name: str
    role: UserRole


class TokenClaims(BaseModel):
    sub: UUID
    exp: int
    type: TokenType
    company_id: UUID | None = None
    role: UserRole | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshedAccessToken(BaseModel):
    access_token: str
    token_type: str
