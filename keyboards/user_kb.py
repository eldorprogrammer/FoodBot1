from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from database.models import Category, MenuItem, CartItem


def request_contact_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍽 Меню"), KeyboardButton(text="🛒 Корзина")],
            [KeyboardButton(text="📦 Мои заказы"), KeyboardButton(text="ℹ️ О нас")],
            [KeyboardButton(text="🔐 Админ-панель")],
        ],
        resize_keyboard=True,
    )


def admin_auth_cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )


def categories_kb(categories: list[Category]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=c.name, callback_data=f"cat:{c.id}")] for c in categories]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def items_kb(items: list[MenuItem], category_id: int) -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        status = "" if item.is_available else " ⛔ нет в наличии"
        text = f"{item.name} — {item.price:.0f}₽{status}"
        rows.append([InlineKeyboardButton(text=text, callback_data=f"item:{item.id}")])
    rows.append([InlineKeyboardButton(text="⬅️ К категориям", callback_data="back_to_categories")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def item_detail_kb(item: MenuItem) -> InlineKeyboardMarkup:
    if item.is_available:
        rows = [
            [
                InlineKeyboardButton(text="➕ В корзину", callback_data=f"addcart:{item.id}"),
            ],
        ]
    else:
        rows = [[InlineKeyboardButton(text="⛔ Нет в наличии", callback_data="noop")]]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cat:{item.category_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cart_kb(cart_items: list[CartItem]) -> InlineKeyboardMarkup:
    rows = []
    for ci in cart_items:
        available_mark = "" if ci.menu_item.is_available else " ⚠️ ушло из наличия"
        rows.append([
            InlineKeyboardButton(text=f"{ci.menu_item.name} x{ci.quantity}{available_mark}", callback_data="noop"),
        ])
        rows.append([
            InlineKeyboardButton(text="➖", callback_data=f"cartdec:{ci.id}"),
            InlineKeyboardButton(text="➕", callback_data=f"cartinc:{ci.id}"),
            InlineKeyboardButton(text="🗑", callback_data=f"cartdel:{ci.id}"),
        ])
    if cart_items:
        rows.append([InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout_start")])
        rows.append([InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="cart_clear")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_method_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Оплата при получении", callback_data="pay:cash")],
        [InlineKeyboardButton(text="💳 Оплата онлайн", callback_data="pay:online")],
    ])


def confirm_skip_comment_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить", callback_data="skip_comment")],
    ])


def use_saved_kb(label: str, callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Использовать: {label}", callback_data=callback_data)],
    ])
