from pydantic import BaseModel


class LoginFormRequest(BaseModel):
    username: str
    password: str


class LoginJsonRequest(BaseModel):
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordResetRequestRequest(BaseModel):
    email: str


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str
