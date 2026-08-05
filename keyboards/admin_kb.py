from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from database.models import Category, MenuItem, Order, OrderStatus


def admin_main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Категории"), KeyboardButton(text="🍔 Блюда")],
            [KeyboardButton(text="🧾 Заказы"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="⬅️ Выйти из админки")],
        ],
        resize_keyboard=True,
    )


def admin_cancel_kb() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой «Назад», которая показывается во время ввода
    данных (название, цена, описание и т.д.), чтобы можно было выйти
    из действия, не завершая его."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад")]],
        resize_keyboard=True,
    )


def admin_categories_kb(categories: list[Category]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{c.name}", callback_data=f"a_cat_view:{c.id}")]
        for c in categories
    ]
    rows.append([InlineKeyboardButton(text="➕ Добавить категорию", callback_data="a_cat_new")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_category_detail_kb(category: Category) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍔 Блюда категории", callback_data=f"a_items_list:{category.id}")],
        [InlineKeyboardButton(text="✏️ Переименовать", callback_data=f"a_cat_rename:{category.id}")],
        [InlineKeyboardButton(text="🗑 Удалить категорию", callback_data=f"a_cat_del:{category.id}")],
        [InlineKeyboardButton(text="⬅️ К категориям", callback_data="a_cat_back")],
    ])


def admin_items_kb(items: list[MenuItem], category_id: int) -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        mark = "✅" if item.is_available else "⛔"
        rows.append([InlineKeyboardButton(text=f"{mark} {item.name} — {item.price:.0f}₽",
                                           callback_data=f"a_item_view:{item.id}")])
    rows.append([InlineKeyboardButton(text="➕ Добавить блюдо", callback_data=f"a_item_new:{category_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"a_cat_view:{category_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_item_detail_kb(item: MenuItem) -> InlineKeyboardMarkup:
    toggle_text = "⛔ Снять с продажи" if item.is_available else "✅ Вернуть в наличие"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data=f"a_item_toggle:{item.id}")],
        [InlineKeyboardButton(text="✏️ Название", callback_data=f"a_item_edit:{item.id}:name"),
         InlineKeyboardButton(text="✏️ Цена", callback_data=f"a_item_edit:{item.id}:price")],
        [InlineKeyboardButton(text="✏️ Описание", callback_data=f"a_item_edit:{item.id}:description"),
         InlineKeyboardButton(text="🖼 Фото", callback_data=f"a_item_edit:{item.id}:photo")],
        [InlineKeyboardButton(text="🗑 Удалить блюдо", callback_data=f"a_item_del:{item.id}")],
        [InlineKeyboardButton(text="⬅️ К списку", callback_data=f"a_items_list:{item.category_id}")],
    ])


ORDER_STATUS_LABELS = {
    OrderStatus.NEW: "🆕 Новый",
    OrderStatus.CONFIRMED: "👍 Принят",
    OrderStatus.COOKING: "👨‍🍳 Готовится",
    OrderStatus.DELIVERING: "🛵 В доставке",
    OrderStatus.COMPLETED: "✅ Выполнен",
    OrderStatus.CANCELLED: "❌ Отменён",
}

ORDER_STATUS_FLOW = {
    OrderStatus.NEW: OrderStatus.CONFIRMED,
    OrderStatus.CONFIRMED: OrderStatus.COOKING,
    OrderStatus.COOKING: OrderStatus.DELIVERING,
    OrderStatus.DELIVERING: OrderStatus.COMPLETED,
}


def admin_orders_list_kb(orders: list[Order]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=f"#{o.id} — {ORDER_STATUS_LABELS[o.status]} — {o.total_amount:.0f}₽",
            callback_data=f"a_order_view:{o.id}",
        )]
        for o in orders
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows or [[InlineKeyboardButton(text="Пока пусто", callback_data="noop")]])


def admin_order_detail_kb(order: Order) -> InlineKeyboardMarkup:
    rows = []
    next_status = ORDER_STATUS_FLOW.get(order.status)
    if next_status:
        rows.append([InlineKeyboardButton(
            text=f"➡️ {ORDER_STATUS_LABELS[next_status]}",
            callback_data=f"a_order_status:{order.id}:{next_status.value}",
        )])
    if order.status not in (OrderStatus.COMPLETED, OrderStatus.CANCELLED):
        rows.append([InlineKeyboardButton(text="❌ Отменить заказ",
                                           callback_data=f"a_order_status:{order.id}:cancelled")])
    rows.append([InlineKeyboardButton(text="⬅️ К списку заказов", callback_data="a_orders_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
