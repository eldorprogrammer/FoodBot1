from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import get_order, get_orders_by_status, update_order_status
from database.models import OrderStatus
from handlers.admin import IsAdmin
from keyboards.admin_kb import ORDER_STATUS_LABELS, admin_order_detail_kb, admin_orders_list_kb

router = Router(name="admin_orders")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

ACTIVE_STATUSES = [
    OrderStatus.NEW,
    OrderStatus.CONFIRMED,
    OrderStatus.COOKING,
    OrderStatus.DELIVERING,
]


def _order_text(order) -> str:
    lines = [f"<b>Заказ #{order.id}</b> — {ORDER_STATUS_LABELS[order.status]}"]
    for item in order.items:
        lines.append(f"• {item.name_snapshot} x{item.quantity} = {float(item.price_snapshot) * item.quantity:.0f}₽")
    lines.append(f"Итого: {order.total_amount:.0f}₽")
    lines.append(f"Оплата: {'онлайн' if order.payment_method.value == 'online' else 'при получении'}"
                 f" ({order.payment_status.value})")
    lines.append(f"Адрес: {order.address}")
    lines.append(f"Телефон: {order.phone}")
    if order.comment:
        lines.append(f"Комментарий: {order.comment}")
    return "\n".join(lines)


@router.message(F.text == "🧾 Заказы")
async def list_orders(message: Message, session: AsyncSession):
    orders = await get_orders_by_status(session, ACTIVE_STATUSES)
    await message.answer("Активные заказы:", reply_markup=admin_orders_list_kb(orders))


@router.callback_query(F.data == "a_orders_back")
async def orders_back(callback: CallbackQuery, session: AsyncSession):
    orders = await get_orders_by_status(session, ACTIVE_STATUSES)
    await callback.message.edit_text("Активные заказы:", reply_markup=admin_orders_list_kb(orders))
    await callback.answer()


@router.callback_query(F.data.startswith("a_order_view:"))
async def order_view(callback: CallbackQuery, session: AsyncSession):
    order_id = int(callback.data.split(":")[1])
    order = await get_order(session, order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    await callback.message.edit_text(_order_text(order), parse_mode="HTML",
                                      reply_markup=admin_order_detail_kb(order))
    await callback.answer()


@router.callback_query(F.data.startswith("a_order_status:"))
async def order_change_status(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    _, order_id, new_status = callback.data.split(":")
    order = await update_order_status(session, int(order_id), OrderStatus(new_status))
    await callback.message.edit_text(_order_text(order), parse_mode="HTML",
                                      reply_markup=admin_order_detail_kb(order))
    await callback.answer("Статус обновлён")

    # уведомляем клиента об изменении статуса
    customer = order.user
    try:
        await bot.send_message(
            customer.telegram_id,
            f"Статус вашего заказа #{order.id} изменён: {ORDER_STATUS_LABELS[order.status]}",
        )
    except Exception:
        pass  # клиент мог заблокировать бота — это не критично для админ-панели
