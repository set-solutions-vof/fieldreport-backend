from typing import Literal
from uuid import UUID

from pydantic import BaseModel

UserRole = Literal["admin", "inspector"]


class LoginCredentials(BaseModel):
    email: str
    password: str


class AuthenticatedUser(BaseModel):
    id: UUID
    company_id: UUID
    email: str
    password_hash: str
    name: str
    role: UserRole


class CurrentUser(BaseModel):
    id: UUID
    company_id: UUID
    email: str
    name: str
    role: UserRole


class TokenClaims(BaseModel):
    sub: UUID
    exp: int
    type: Literal["access", "refresh"]
    company_id: UUID | None = None
    role: UserRole | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshedAccessToken(BaseModel):
    access_token: str
    token_type: str
