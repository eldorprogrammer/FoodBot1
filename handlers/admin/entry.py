from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database.crud import get_or_create_user, set_user_admin
from handlers.admin import IsAdmin
from keyboards.admin_kb import admin_main_kb
from keyboards.user_kb import main_menu_kb

router = Router(name="admin_entry")
router.message.filter(IsAdmin())


@router.message(Command("admin"))
async def open_admin(message: Message):
    await message.answer("Панель администратора:", reply_markup=admin_main_kb())


@router.message(F.text == "⬅️ Выйти из админки")
async def close_admin(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    # Снимаем права, выданные через вход по логину/паролю. Для тех, кто
    # прописан в ADMIN_IDS, права автоматически вернутся при следующем
    # обращении (см. get_or_create_user) — это ожидаемо для "постоянных" админов.
    if message.from_user.id not in config.admin_ids:
        db_user = await get_or_create_user(
            session, message.from_user.id, message.from_user.username, message.from_user.full_name
        )
        await set_user_admin(session, db_user.id, False)
    await message.answer("Вы вышли из админ-панели.", reply_markup=main_menu_kb())
