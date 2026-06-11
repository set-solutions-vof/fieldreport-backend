import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt

from src.db.auth import queries as auth_queries
from src.db.password_reset import queries as reset_queries
from src.db.user import queries as user_queries
from src.email.password_reset_email import send_password_reset_email
from src.exceptions import InvalidResetToken, InviteEmailDeliveryFailed


async def request_reset(email: str) -> None:
    user = await auth_queries.get_user_by_email(email)

    if user is None:
        return

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(hours=1)
    await reset_queries.create_reset_token(str(user.id), token_hash, expires_at)

    try:
        await send_password_reset_email(to_email=email, token=token)
    except Exception as error:
        raise InviteEmailDeliveryFailed() from error


async def confirm_reset(token: str, new_password: str) -> None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    row = await reset_queries.get_valid_reset_token(token_hash)

    if row is None:
        raise InvalidResetToken()

    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    await user_queries.update_user_password(str(row["user_id"]), new_hash)
    await reset_queries.mark_token_used(str(row["id"]))
