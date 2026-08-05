import time

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database.crud import get_or_create_user, set_user_admin
from keyboards.admin_kb import admin_main_kb
from keyboards.user_kb import admin_auth_cancel_kb, main_menu_kb
from states.states import AdminAuthStates

router = Router(name="admin_auth")

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 5 * 60

# telegram_id -> (кол-во неудачных попыток, время окончания блокировки)
_failed_attempts: dict[int, list[float]] = {}


def _is_locked_out(telegram_id: int) -> int:
    """Возвращает оставшееся время блокировки в секундах (0, если не заблокирован)."""
    now = time.monotonic()
    attempts = [t for t in _failed_attempts.get(telegram_id, []) if now - t < LOCKOUT_SECONDS]
    _failed_attempts[telegram_id] = attempts
    if len(attempts) >= MAX_ATTEMPTS:
        remaining = LOCKOUT_SECONDS - (now - attempts[0])
        return max(1, int(remaining))
    return 0


def _register_failed_attempt(telegram_id: int) -> None:
    _failed_attempts.setdefault(telegram_id, []).append(time.monotonic())


def _clear_failed_attempts(telegram_id: int) -> None:
    _failed_attempts.pop(telegram_id, None)


@router.message(F.text == "🔐 Админ-панель")
async def admin_panel_button(message: Message, state: FSMContext, session: AsyncSession):
    user = await get_or_create_user(
        session, message.from_user.id, message.from_user.username, message.from_user.full_name
    )
    if user.is_admin or message.from_user.id in config.admin_ids:
        await message.answer("Панель администратора:", reply_markup=admin_main_kb())
        return

    if not config.admin_login or not config.admin_password:
        await message.answer(
            "Вход в админ-панель ещё не настроен. Задайте ADMIN_LOGIN и ADMIN_PASSWORD в .env."
        )
        return

    locked_for = _is_locked_out(message.from_user.id)
    if locked_for:
        minutes = locked_for // 60 + 1
        await message.answer(
            f"Слишком много неудачных попыток входа. Попробуйте снова через ~{minutes} мин."
        )
        return

    await state.set_state(AdminAuthStates.waiting_login)
    await message.answer("Введите логин:", reply_markup=admin_auth_cancel_kb())


@router.message(AdminAuthStates.waiting_login, F.text == "❌ Отмена")
@router.message(AdminAuthStates.waiting_password, F.text == "❌ Отмена")
async def admin_auth_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Вход отменён.", reply_markup=main_menu_kb())


@router.message(AdminAuthStates.waiting_login)
async def admin_auth_login(message: Message, state: FSMContext):
    locked_for = _is_locked_out(message.from_user.id)
    if locked_for:
        await state.clear()
        minutes = locked_for // 60 + 1
        await message.answer(
            f"Слишком много неудачных попыток входа. Попробуйте снова через ~{minutes} мин.",
            reply_markup=main_menu_kb(),
        )
        return

    await state.update_data(login=message.text or "")
    await state.set_state(AdminAuthStates.waiting_password)
    await message.answer("Введите пароль:", reply_markup=admin_auth_cancel_kb())


@router.message(AdminAuthStates.waiting_password)
async def admin_auth_password(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    entered_login = data.get("login", "")
    entered_password = message.text or ""
    await state.clear()

    if entered_login == config.admin_login and entered_password == config.admin_password:
        _clear_failed_attempts(message.from_user.id)
        db_user = await get_or_create_user(
            session, message.from_user.id, message.from_user.username, message.from_user.full_name
        )
        await set_user_admin(session, db_user.id, True)
        await message.answer("Добро пожаловать в панель администратора!", reply_markup=admin_main_kb())
        return

    _register_failed_attempt(message.from_user.id)
    await message.answer(
        "Неверный логин или пароль.",
        reply_markup=main_menu_kb(),
    )
