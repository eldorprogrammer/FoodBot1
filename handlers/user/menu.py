from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import get_active_categories, get_item, get_items_by_category
from handlers.user.filters import IsRegistered
from keyboards.user_kb import categories_kb, item_detail_kb, items_kb

router = Router(name="menu")
router.message.filter(IsRegistered())
router.callback_query.filter(IsRegistered())


@router.message(F.text == "🍽 Меню")
async def show_categories(message: Message, session: AsyncSession):
    categories = await get_active_categories(session)
    if not categories:
        await message.answer("Меню пока не заполнено. Загляните позже.")
        return
    await message.answer("Выберите категорию:", reply_markup=categories_kb(categories))


@router.callback_query(F.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery, session: AsyncSession):
    categories = await get_active_categories(session)
    await callback.message.edit_text("Выберите категорию:", reply_markup=categories_kb(categories))
    await callback.answer()


@router.callback_query(F.data.startswith("cat:"))
async def show_items(callback: CallbackQuery, session: AsyncSession):
    category_id = int(callback.data.split(":")[1])
    items = await get_items_by_category(session, category_id)
    if not items:
        await callback.answer("В этой категории пока нет блюд", show_alert=True)
        return
    text = (
        "Блюда категории (⛔ — временно нет в наличии, заказать нельзя):"
    )
    try:
        await callback.message.edit_text(text, reply_markup=items_kb(items, category_id))
    except Exception:
        # если предыдущее сообщение было с фото (edit_text к нему не применим)
        await callback.message.answer(text, reply_markup=items_kb(items, category_id))
    await callback.answer()


@router.callback_query(F.data.startswith("item:"))
async def show_item_detail(callback: CallbackQuery, session: AsyncSession):
    item_id = int(callback.data.split(":")[1])
    item = await get_item(session, item_id)
    if not item:
        await callback.answer("Блюдо не найдено", show_alert=True)
        return

    availability_line = "✅ В наличии" if item.is_available else "⛔ Сейчас нет в наличии"
    caption = (
        f"<b>{item.name}</b>\n"
        f"{item.description or ''}\n\n"
        f"Цена: {item.price:.0f}₽\n"
        f"{availability_line}"
    )

    if item.photo_file_id:
        await callback.message.answer_photo(
            item.photo_file_id, caption=caption, parse_mode="HTML", reply_markup=item_detail_kb(item)
        )
    else:
        await callback.message.answer(caption, parse_mode="HTML", reply_markup=item_detail_kb(item))
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()
