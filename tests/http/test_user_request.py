from src.http.v1.request.user import ChangePasswordRequest, UpdateProfileRequest


def test_update_profile_request_accepts_name() -> None:
    request = UpdateProfileRequest(name="Jane Inspector")

    assert request.name == "Jane Inspector"


def test_change_password_request_accepts_password_fields() -> None:
    request = ChangePasswordRequest(
        current_password="CurrentPassword2026!",
        new_password="NewPassword2026!",
    )

    assert request.current_password == "CurrentPassword2026!"
    assert request.new_password == "NewPassword2026!"
