from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import (
    add_to_cart,
    clear_cart,
    get_cart,
    get_item,
    get_or_create_user,
    remove_cart_item,
    set_cart_item_quantity,
)
from handlers.user.filters import IsRegistered
from keyboards.user_kb import cart_kb

router = Router(name="cart")
router.message.filter(IsRegistered())
router.callback_query.filter(IsRegistered())


def _cart_text(cart_items) -> str:
    if not cart_items:
        return "Ваша корзина пуста. Загляните в 🍽 Меню, чтобы выбрать блюда."
    lines = ["Ваша корзина:\n"]
    total = 0
    for ci in cart_items:
        line_total = float(ci.menu_item.price) * ci.quantity
        total += line_total
        lines.append(f"• {ci.menu_item.name} x{ci.quantity} = {line_total:.0f}₽")
    lines.append(f"\nИтого: {total:.0f}₽")
    return "\n".join(lines)


async def _get_user(session: AsyncSession, message_or_callback):
    from_user = message_or_callback.from_user
    return await get_or_create_user(session, from_user.id, from_user.username, from_user.full_name)


@router.message(F.text == "🛒 Корзина")
async def show_cart(message: Message, session: AsyncSession):
    user = await _get_user(session, message)
    cart_items = await get_cart(session, user.id)
    await message.answer(_cart_text(cart_items), reply_markup=cart_kb(cart_items))


@router.callback_query(F.data.startswith("addcart:"))
async def add_item_to_cart(callback: CallbackQuery, session: AsyncSession):
    item_id = int(callback.data.split(":")[1])
    item = await get_item(session, item_id)
    if not item or not item.is_available:
        await callback.answer("Это блюдо сейчас недоступно 😔", show_alert=True)
        return
    user = await _get_user(session, callback)
    await add_to_cart(session, user.id, item_id, 1)
    await callback.answer("Добавлено в корзину ✅")


async def _refresh_cart_message(callback: CallbackQuery, session: AsyncSession):
    user = await _get_user(session, callback)
    cart_items = await get_cart(session, user.id)
    await callback.message.edit_text(_cart_text(cart_items), reply_markup=cart_kb(cart_items))


@router.callback_query(F.data.startswith("cartinc:"))
async def cart_increment(callback: CallbackQuery, session: AsyncSession):
    cart_item_id = int(callback.data.split(":")[1])
    cart_items = await get_cart(session, (await _get_user(session, callback)).id)
    target = next((c for c in cart_items if c.id == cart_item_id), None)
    if target:
        if not target.menu_item.is_available:
            await callback.answer("Блюдо сейчас недоступно, увеличить нельзя", show_alert=True)
            return
        await set_cart_item_quantity(session, cart_item_id, target.quantity + 1)
    await _refresh_cart_message(callback, session)
    await callback.answer()


@router.callback_query(F.data.startswith("cartdec:"))
async def cart_decrement(callback: CallbackQuery, session: AsyncSession):
    cart_item_id = int(callback.data.split(":")[1])
    cart_items = await get_cart(session, (await _get_user(session, callback)).id)
    target = next((c for c in cart_items if c.id == cart_item_id), None)
    if target:
        await set_cart_item_quantity(session, cart_item_id, target.quantity - 1)
    await _refresh_cart_message(callback, session)
    await callback.answer()


@router.callback_query(F.data.startswith("cartdel:"))
async def cart_delete(callback: CallbackQuery, session: AsyncSession):
    cart_item_id = int(callback.data.split(":")[1])
    await remove_cart_item(session, cart_item_id)
    await _refresh_cart_message(callback, session)
    await callback.answer("Удалено")


@router.callback_query(F.data == "cart_clear")
async def cart_clear(callback: CallbackQuery, session: AsyncSession):
    user = await _get_user(session, callback)
    await clear_cart(session, user.id)
    await _refresh_cart_message(callback, session)
    await callback.answer("Корзина очищена")
