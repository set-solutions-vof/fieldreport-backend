import pytest
from pydantic import ValidationError

from src.http.v1.request.invite import AcceptInviteRequest


def test_accept_invite_request_requires_password() -> None:
    request = AcceptInviteRequest(password="secret12")

    assert request.password == "secret12"


def test_accept_invite_request_rejects_missing_password() -> None:
    with pytest.raises(ValidationError):
        AcceptInviteRequest.model_validate({})
