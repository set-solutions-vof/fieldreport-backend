from src.config import settings
from src.email.invite_email import (
    body_style,
    body_text_style,
    brand_style,
    button_style,
    card_style,
    footer_style,
    heading_style,
)
from src.email.smtp_client import send_email


async def send_password_reset_email(*, to_email: str, token: str) -> None:
    reset_url = password_reset_url(token)
    subject = "Wachtwoord herstellen — FieldReport"
    text_body = (
        "Je hebt een verzoek gedaan om je wachtwoord voor FieldReport te herstellen.\n\n"
        f"Stel een nieuw wachtwoord in via deze link:\n{reset_url}\n\n"
        "Deze link is 1 uur geldig. Als je dit niet hebt aangevraagd, kun je deze e-mail negeren."
    )
    html_body = f"""<!DOCTYPE html>
<html lang="nl">
  <body style="{body_style}">
    <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
      <tr>
        <td align="center">
          <table
            width="560"
            cellpadding="0"
            cellspacing="0"
            role="presentation"
            style="{card_style}"
          >
            <tr>
              <td>
                <p style="{brand_style}">FieldReport</p>
                <h1 style="{heading_style}">Wachtwoord herstellen</h1>
                <p style="{body_text_style}">
                  Je hebt een verzoek gedaan om je wachtwoord voor FieldReport te herstellen.
                </p>
                <p style="margin:0 0 24px;">
                  <a href="{reset_url}" style="{button_style}">
                    Nieuw wachtwoord instellen
                  </a>
                </p>
                <p style="{footer_style}">
                  Deze link is 1 uur geldig. Als je dit niet hebt aangevraagd,
                  kun je deze e-mail negeren. Als de knop niet werkt,
                  open dan deze link:<br />
                  <a href="{reset_url}" style="color:#3b5bdb;">{reset_url}</a>
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""

    await send_email(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )


def password_reset_url(token: str) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/reset-password/{token}"
