from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database.crud import (
    clear_cart,
    create_order,
    get_cart,
    get_order,
    get_or_create_user,
    mark_order_paid,
    update_user_contact,
)
from database.models import PaymentMethod
from handlers.user.filters import IsRegistered
from keyboards.user_kb import confirm_skip_comment_kb, main_menu_kb, payment_method_kb, use_saved_kb
from states.states import CheckoutStates

router = Router(name="checkout")
router.message.filter(IsRegistered())
router.callback_query.filter(IsRegistered())


async def _get_user(session: AsyncSession, from_user):
    return await get_or_create_user(session, from_user.id, from_user.username, from_user.full_name)


@router.callback_query(F.data == "checkout_start")
async def checkout_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await _get_user(session, callback.from_user)
    cart_items = await get_cart(session, user.id)

    if not cart_items:
        await callback.answer("Корзина пуста", show_alert=True)
        return

    unavailable = [ci for ci in cart_items if not ci.menu_item.is_available]
    if unavailable:
        names = ", ".join(ci.menu_item.name for ci in unavailable)
        await callback.answer(
            f"Некоторые блюда закончились и их нужно убрать из корзины: {names}",
            show_alert=True,
        )
        return

    await state.set_state(CheckoutStates.waiting_address)
    await callback.message.answer("Укажите адрес доставки:")
    if user.last_address:
        await callback.message.answer(
            "Или используйте адрес из прошлого заказа:",
            reply_markup=use_saved_kb(user.last_address, "use_saved_address"),
        )
    await callback.answer()


@router.callback_query(F.data == "use_saved_address", CheckoutStates.waiting_address)
async def use_saved_address(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await _get_user(session, callback.from_user)
    await state.update_data(address=user.last_address)
    await _ask_phone(callback.message, user, state)
    await callback.answer()


@router.message(CheckoutStates.waiting_address)
async def checkout_address(message: Message, session: AsyncSession, state: FSMContext):
    await state.update_data(address=message.text)
    user = await _get_user(session, message.from_user)
    await _ask_phone(message, user, state)


async def _ask_phone(message: Message, user, state: FSMContext):
    await state.set_state(CheckoutStates.waiting_phone)
    await message.answer("Укажите номер телефона для связи:")
    if user.phone:
        await message.answer(
            "Или используйте сохранённый номер:",
            reply_markup=use_saved_kb(user.phone, "use_saved_phone"),
        )


@router.callback_query(F.data == "use_saved_phone", CheckoutStates.waiting_phone)
async def use_saved_phone(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await _get_user(session, callback.from_user)
    await state.update_data(phone=user.phone)
    await state.set_state(CheckoutStates.waiting_comment)
    await callback.message.answer(
        "Комментарий к заказу (например, домофон, этаж) — или нажмите «Пропустить»:",
        reply_markup=confirm_skip_comment_kb(),
    )
    await callback.answer()


@router.message(CheckoutStates.waiting_phone)
async def checkout_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(CheckoutStates.waiting_comment)
    await message.answer(
        "Комментарий к заказу (например, домофон, этаж) — или нажмите «Пропустить»:",
        reply_markup=confirm_skip_comment_kb(),
    )


@router.callback_query(F.data == "skip_comment", CheckoutStates.waiting_comment)
async def skip_comment(callback: CallbackQuery, state: FSMContext):
    await state.update_data(comment=None)
    await state.set_state(CheckoutStates.waiting_payment_method)
    await callback.message.answer("Выберите способ оплаты:", reply_markup=payment_method_kb())
    await callback.answer()


@router.message(CheckoutStates.waiting_comment)
async def checkout_comment(message: Message, state: FSMContext):
    await state.update_data(comment=message.text)
    await state.set_state(CheckoutStates.waiting_payment_method)
    await message.answer("Выберите способ оплаты:", reply_markup=payment_method_kb())


@router.callback_query(F.data == "pay:cash", CheckoutStates.waiting_payment_method)
async def pay_cash(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    order = await _finalize_order(session, callback.from_user, state, PaymentMethod.CASH)
    await state.clear()
    await callback.message.answer(
        f"Заказ #{order.id} оформлен! Оплата — при получении.\n"
        f"Сумма: {order.total_amount:.0f}₽\n"
        "Мы пришлём уведомление, когда статус заказа изменится.",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "pay:online", CheckoutStates.waiting_payment_method)
async def pay_online(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    if not config.payments_provider_token:
        await callback.answer(
            "Онлайн-оплата временно недоступна, выберите оплату при получении", show_alert=True
        )
        return

    order = await _finalize_order(session, callback.from_user, state, PaymentMethod.ONLINE)
    await state.update_data(pending_order_id=order.id)

    prices = [LabeledPrice(label=f"Заказ #{order.id}", amount=int(round(float(order.total_amount) * 100)))]
    await callback.message.answer_invoice(
        title=f"Оплата заказа #{order.id}",
        description=f"{config.restaurant_name} — оплата заказа",
        payload=f"order:{order.id}",
        provider_token=config.payments_provider_token,
        currency=config.currency,
        prices=prices,
    )
    await callback.answer()


async def _finalize_order(session: AsyncSession, from_user, state: FSMContext, method: PaymentMethod):
    data = await state.get_data()
    user = await _get_user(session, from_user)
    cart_items = await get_cart(session, user.id)

    order = await create_order(
        session,
        user_id=user.id,
        address=data["address"],
        phone=data["phone"],
        payment_method=method,
        comment=data.get("comment"),
        cart_items=cart_items,
    )
    await update_user_contact(session, user.id, phone=data["phone"], address=data["address"])
    await clear_cart(session, user.id)
    return order


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    # Здесь можно повторно проверить наличие блюд перед подтверждением оплаты
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, session: AsyncSession, state: FSMContext):
    payload = message.successful_payment.invoice_payload  # формат "order:<id>"
    order_id = int(payload.split(":")[1])
    await mark_order_paid(session, order_id)
    order = await get_order(session, order_id)
    await state.clear()
    await message.answer(
        f"Оплата получена ✅\nЗаказ #{order.id} на сумму {order.total_amount:.0f}₽ передан в работу.",
        reply_markup=main_menu_kb(),
    )
