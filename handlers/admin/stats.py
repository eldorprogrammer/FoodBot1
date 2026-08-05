from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import get_today_stats
from handlers.admin import IsAdmin

router = Router(name="admin_stats")
router.message.filter(IsAdmin())


@router.message(F.text == "📊 Статистика")
async def show_stats(message: Message, session: AsyncSession):
    stats = await get_today_stats(session)
    await message.answer(
        "Статистика за сегодня:\n"
        f"Заказов: {stats['count']}\n"
        f"Выручка: {stats['revenue']:.0f}₽"
    )
