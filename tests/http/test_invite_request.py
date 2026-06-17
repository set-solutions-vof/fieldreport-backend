import pytest
from pydantic import ValidationError

from src.http.v1.request.invite import AcceptInviteRequest


def test_accept_invite_request_requires_name_and_password() -> None:
    request = AcceptInviteRequest(name="New User", password="secret12")

    assert request.name == "New User"
    assert request.password == "secret12"


def test_accept_invite_request_rejects_missing_fields() -> None:
    with pytest.raises(ValidationError):
        AcceptInviteRequest.model_validate({"name": "New User"})
