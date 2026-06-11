from collections.abc import Mapping

from src.models.auth.authentication import AuthenticatedUser, CurrentUser


def map_authenticated_user(row: Mapping[str, object]) -> AuthenticatedUser:
    return AuthenticatedUser.model_validate(dict(row))


def map_current_user(row: Mapping[str, object]) -> CurrentUser:
    return CurrentUser.model_validate(dict(row))
