import bcrypt

from src.db.user import queries as db_queries
from src.exceptions import PasswordIncorrect
from src.models.auth.authentication import CurrentUser


async def update_profile(current_user: CurrentUser, name: str) -> CurrentUser:
    await db_queries.update_user_name(str(current_user.id), name)

    return current_user.model_copy(update={"name": name})


async def change_password(user_id: str, current_password: str, new_password: str) -> None:
    password_hash = await db_queries.get_user_password_hash(user_id)

    if not bcrypt.checkpw(current_password.encode(), password_hash.encode()):
        raise PasswordIncorrect()

    new_password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
    await db_queries.update_user_password(user_id, new_password_hash.decode())
