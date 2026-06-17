from unittest.mock import AsyncMock, patch

from src.email.password_reset_email import password_reset_url, send_password_reset_email


def test_password_reset_url_builds_frontend_link() -> None:
    assert password_reset_url("raw-token") == "http://localhost:5173/reset-password/raw-token"


async def test_send_password_reset_email_sends_message() -> None:
    with patch("src.email.password_reset_email.send_email", AsyncMock()) as send_email:
        await send_password_reset_email(
            to_email="user@example.com",
            token="raw-token",
        )

    send_email.assert_awaited_once()
    assert send_email.await_args.kwargs["to_email"] == "user@example.com"
    assert send_email.await_args.kwargs["subject"] == "Wachtwoord herstellen — FieldReport"
    assert (
        "http://localhost:5173/reset-password/raw-token"
        in send_email.await_args.kwargs["text_body"]
    )
    assert "1 uur geldig" in send_email.await_args.kwargs["text_body"]
