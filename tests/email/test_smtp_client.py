from unittest.mock import AsyncMock, patch

from src.email.smtp_client import send_email


async def test_send_email_sends_message_via_smtp() -> None:
    with patch("src.email.smtp_client.aiosmtplib.send", AsyncMock()) as send_email_transport:
        await send_email(
            to_email="new.user@example.com",
            subject="Subject",
            text_body="Plain text",
            html_body="<p>HTML</p>",
        )

    send_email_transport.assert_awaited_once()
    message = send_email_transport.await_args.args[0]
    assert message["To"] == "new.user@example.com"
    assert message["Subject"] == "Subject"
