from aiogram.filters import Filter
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import get_or_create_user


class IsRegistered(Filter):
    """Пропускает дальше только зарегистрированных пользователей.
    Не блокирует админов — им регистрация не требуется."""

    async def __call__(self, event: TelegramObject, session: AsyncSession) -> bool:
        from_user = getattr(event, "from_user", None)
        if not from_user:
            return False
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.full_name)
        return user.is_registered or user.is_admin
