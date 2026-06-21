from src.http.v1.request.user import ChangePasswordRequest, UpdateProfileRequest


def test_update_profile_request_accepts_first_and_last_name() -> None:
    request = UpdateProfileRequest(first_name="Jane", last_name="Inspector")

    assert request.first_name == "Jane"
    assert request.last_name == "Inspector"


def test_change_password_request_accepts_password_fields() -> None:
    request = ChangePasswordRequest(
        current_password="CurrentPassword2026!",
        new_password="NewPassword2026!",
    )

    assert request.current_password == "CurrentPassword2026!"
    assert request.new_password == "NewPassword2026!"
