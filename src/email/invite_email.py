from src.config import settings
from src.email.smtp_client import send_email
from src.models.enums.user_role import UserRole


def invite_accept_url(token: str) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/invite/{token}"


def role_label(role: UserRole) -> str:
    if role == "admin":
        return "Beheerder"
    return "Inspecteur"


body_style = "margin:0;padding:32px;background:#f4f6f8;font-family:Arial,sans-serif;color:#1f2937;"
card_style = "background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;padding:32px;"
brand_style = (
    "margin:0 0 8px;font-size:12px;font-weight:700;letter-spacing:0.08em;"
    "text-transform:uppercase;color:#3b5bdb;"
)
heading_style = "margin:0 0 12px;font-size:24px;line-height:1.3;color:#111827;"
body_text_style = "margin:0 0 20px;font-size:15px;line-height:1.6;color:#4b5563;"
button_style = (
    "display:inline-block;padding:12px 20px;background:#3b5bdb;color:#ffffff;"
    "text-decoration:none;border-radius:8px;font-weight:600;"
)
footer_style = "margin:0;font-size:13px;line-height:1.6;color:#6b7280;"


async def send_invite_email(
    *,
    to_email: str,
    company_name: str,
    role: UserRole,
    token: str,
) -> None:
    accept_url = invite_accept_url(token)
    role_text = role_label(role)
    subject = f"Je bent uitgenodigd voor {company_name} op FieldReport"
    text_body = (
        f"Je bent uitgenodigd om deel te nemen aan {company_name} op FieldReport "
        f"als {role_text}.\n\n"
        f"Accepteer je uitnodiging via deze link:\n{accept_url}\n\n"
        "Deze uitnodiging verloopt over 7 dagen."
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
                <h1 style="{heading_style}">Je bent uitgenodigd</h1>
                <p style="{body_text_style}">
                  Je bent uitgenodigd om deel te nemen aan
                  <strong>{company_name}</strong> als <strong>{role_text}</strong>.
                </p>
                <p style="margin:0 0 24px;">
                  <a href="{accept_url}" style="{button_style}">
                    Uitnodiging accepteren
                  </a>
                </p>
                <p style="{footer_style}">
                  Deze uitnodiging verloopt over 7 dagen. Als de knop niet werkt,
                  open dan deze link:<br />
                  <a href="{accept_url}" style="color:#3b5bdb;">{accept_url}</a>
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
