from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import get_or_create_user, get_user_orders
from handlers.user.filters import IsRegistered
from keyboards.admin_kb import ORDER_STATUS_LABELS

router = Router(name="history")
router.message.filter(IsRegistered())


@router.message(F.text == "📦 Мои заказы")
async def show_history(message: Message, session: AsyncSession):
    user = await get_or_create_user(
        session, message.from_user.id, message.from_user.username, message.from_user.full_name
    )
    orders = await get_user_orders(session, user.id)

    if not orders:
        await message.answer("У вас пока нет заказов.")
        return

    for order in orders:
        lines = [f"<b>Заказ #{order.id}</b> — {ORDER_STATUS_LABELS[order.status]}"]
        for item in order.items:
            lines.append(f"• {item.name_snapshot} x{item.quantity} = {float(item.price_snapshot) * item.quantity:.0f}₽")
        lines.append(f"Итого: {order.total_amount:.0f}₽")
        lines.append(f"Адрес: {order.address}")
        lines.append(order.created_at.strftime("Дата: %d.%m.%Y %H:%M"))
        await message.answer("\n".join(lines), parse_mode="HTML")
