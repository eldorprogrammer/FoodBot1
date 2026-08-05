from aiogram import Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import get_or_create_user
from keyboards.user_kb import main_menu_kb

router = Router(name="fallback")


@router.message()
async def fallback_message(message: Message, session: AsyncSession):
    user = await get_or_create_user(
        session, message.from_user.id, message.from_user.username, message.from_user.full_name
    )
    if not user.is_registered and not user.is_admin:
        await message.answer("Пожалуйста, отправьте /start, чтобы зарегистрироваться и продолжить.")
        return
    await message.answer(
        "Не совсем понял запрос. Воспользуйтесь кнопками меню ниже или командой /help.",
        reply_markup=main_menu_kb(),
    )
