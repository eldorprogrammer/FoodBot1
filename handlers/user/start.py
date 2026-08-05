from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database.crud import complete_registration, get_or_create_user
from keyboards.user_kb import main_menu_kb, request_contact_kb
from states.states import RegistrationStates

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext):
    user = await get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    if user.is_registered:
        await message.answer(
            f"С возвращением в {config.restaurant_name}! 🍽",
            reply_markup=main_menu_kb(),
        )
        return

    await state.set_state(RegistrationStates.waiting_name)
    await message.answer(
        f"Добро пожаловать в {config.restaurant_name}! 🍽\n\n"
        "Прежде чем перейти к меню, давайте зарегистрируемся — это займёт минуту.\n\n"
        "Как к вам обращаться? Введите имя:"
    )


@router.message(RegistrationStates.waiting_name)
async def registration_name(message: Message, state: FSMContext):
    name = message.text.strip() if message.text else ""
    if not name:
        await message.answer("Пожалуйста, введите имя текстом:")
        return
    await state.update_data(full_name=name)
    await state.set_state(RegistrationStates.waiting_phone)
    await message.answer(
        "Отлично! Теперь укажите номер телефона — можно отправить кнопкой ниже "
        "или ввести вручную:",
        reply_markup=request_contact_kb(),
    )


@router.message(RegistrationStates.waiting_phone, F.contact)
async def registration_phone_contact(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await _ask_address(message, state)


@router.message(RegistrationStates.waiting_phone, F.text)
async def registration_phone_text(message: Message, state: FSMContext):
    phone = message.text.strip()
    if len(phone) < 5:
        await message.answer("Похоже на неполный номер. Введите телефон ещё раз:")
        return
    await state.update_data(phone=phone)
    await _ask_address(message, state)


async def _ask_address(message: Message, state: FSMContext):
    await state.set_state(RegistrationStates.waiting_address)
    await message.answer(
        "Спасибо! И последнее — укажите адрес доставки по умолчанию "
        "(можно будет изменить перед конкретным заказом):",
    )


@router.message(RegistrationStates.waiting_address)
async def registration_address(message: Message, session: AsyncSession, state: FSMContext):
    address = message.text.strip() if message.text else ""
    if not address:
        await message.answer("Пожалуйста, введите адрес текстом:")
        return

    data = await state.get_data()
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username,
                                     message.from_user.full_name)
    await complete_registration(session, user.id, data["full_name"], data["phone"], address)
    await state.clear()

    await message.answer(
        f"Регистрация завершена, {data['full_name']}! Добро пожаловать 🎉",
        reply_markup=main_menu_kb(),
    )


@router.message(F.text == "ℹ️ О нас")
async def about(message: Message):
    await message.answer(
        f"{config.restaurant_name}\n\n"
        "Оформляйте заказ через кнопку «🍽 Меню», добавляйте блюда в корзину "
        "и завершайте оформление через «🛒 Корзина».\n"
        "Доступна оплата при получении и оплата онлайн."
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🍽 Меню — посмотреть категории и блюда\n"
        "🛒 Корзина — собранные позиции, оформление заказа\n"
        "📦 Мои заказы — история и статус ваших заказов\n"
        "/admin — панель администратора (только для персонала)"
    )
