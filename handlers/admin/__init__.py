from aiogram.filters import Filter
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database.crud import get_or_create_user


class IsAdmin(Filter):
    """Пропускает как пользователей из ADMIN_IDS (.env), так и тех, кто
    вошёл в панель через кнопку "🔐 Админ-панель" по логину и паролю
    (см. handlers/admin/auth.py) — их статус хранится в БД (User.is_admin)."""

    async def __call__(self, event: TelegramObject, session: AsyncSession) -> bool:
        user = getattr(event, "from_user", None)
        if not user:
            return False
        if user.id in config.admin_ids:
            return True
        db_user = await get_or_create_user(session, user.id, user.username, user.full_name)
        return db_user.is_admin
