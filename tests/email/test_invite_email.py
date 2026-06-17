from unittest.mock import AsyncMock, patch

from src.email.invite_email import invite_accept_url, role_label, send_invite_email


def test_invite_accept_url_builds_frontend_link() -> None:
    assert invite_accept_url("raw-token") == "http://localhost:5173/invite/raw-token"


def test_role_label_returns_dutch_labels() -> None:
    assert role_label("admin") == "Beheerder"
    assert role_label("inspector") == "Inspecteur"


async def test_send_invite_email_sends_message() -> None:
    with patch("src.email.invite_email.send_email", AsyncMock()) as send_email:
        await send_invite_email(
            to_email="new.user@example.com",
            company_name="Demo Company",
            role="admin",
            token="raw-token",
        )

    send_email.assert_awaited_once()
    assert send_email.await_args.kwargs["to_email"] == "new.user@example.com"
    assert "Demo Company" in send_email.await_args.kwargs["subject"]
    assert "http://localhost:5173/invite/raw-token" in send_email.await_args.kwargs["text_body"]
