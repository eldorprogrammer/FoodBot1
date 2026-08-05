from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import (
    create_category,
    create_item,
    delete_category,
    delete_item,
    get_all_categories,
    get_category,
    get_item,
    get_items_by_category,
    rename_category,
    update_item_availability,
    update_item_fields,
    update_item_photo,
)
from database.models import MenuItem
from handlers.admin import IsAdmin
from keyboards.admin_kb import (
    admin_cancel_kb,
    admin_categories_kb,
    admin_category_detail_kb,
    admin_item_detail_kb,
    admin_items_kb,
    admin_main_kb,
)
from states.states import AdminCategoryStates, AdminItemStates

router = Router(name="admin_menu")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def _item_card_text(item: MenuItem) -> str:
    status = "✅ В наличии" if item.is_available else "⛔ Нет в наличии"
    description = item.description or "— описание не добавлено —"
    return f"<b>{item.name}</b>\n{description}\n\nЦена: {item.price:.0f}₽\nСтатус: {status}"


async def _show_item_card(target: Message | CallbackQuery, item: MenuItem, *, replace: bool = False) -> None:
    """Показывает карточку блюда: с фото, если оно есть, иначе просто текстом.
    target может быть исходным Message (например, из хендлера ввода текста)
    или CallbackQuery (тогда карточка отправится в тот же чат).
    Если replace=True и это CallbackQuery — старое сообщение сначала удаляется,
    чтобы не плодить дубликаты карточек в чате."""
    message = target.message if isinstance(target, CallbackQuery) else target
    text = _item_card_text(item)
    kb = admin_item_detail_kb(item)

    if replace and isinstance(target, CallbackQuery):
        try:
            await target.message.delete()
        except Exception:
            pass  # сообщение могло быть уже удалено/недоступно для удаления — не критично

    if item.photo_file_id:
        await message.answer_photo(item.photo_file_id, caption=text, parse_mode="HTML", reply_markup=kb)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=kb)


async def _back_to_categories(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    categories = await get_all_categories(session)
    await message.answer("Отменено.", reply_markup=admin_main_kb())
    await message.answer("Категории меню:", reply_markup=admin_categories_kb(categories))


async def _back_to_items(message: Message, session: AsyncSession, state: FSMContext, category_id: int) -> None:
    await state.clear()
    items = await get_items_by_category(session, category_id)
    await message.answer("Отменено.", reply_markup=admin_main_kb())
    await message.answer(
        "Блюда категории (✅ в наличии / ⛔ нет в наличии):",
        reply_markup=admin_items_kb(items, category_id),
    )


async def _back_to_item_card(message: Message, session: AsyncSession, state: FSMContext, item_id: int) -> None:
    await state.clear()
    item = await get_item(session, item_id)
    await message.answer("Отменено.", reply_markup=admin_main_kb())
    if item:
        await _show_item_card(message, item)


# ---------- Категории ----------

@router.message(F.text == "📋 Категории")
async def list_categories(message: Message, session: AsyncSession):
    categories = await get_all_categories(session)
    await message.answer("Категории меню:", reply_markup=admin_categories_kb(categories))


@router.callback_query(F.data == "a_cat_back")
async def cat_back(callback: CallbackQuery, session: AsyncSession):
    categories = await get_all_categories(session)
    await callback.message.edit_text("Категории меню:", reply_markup=admin_categories_kb(categories))
    await callback.answer()


@router.callback_query(F.data == "a_cat_new")
async def cat_new(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminCategoryStates.waiting_name)
    await callback.message.answer("Введите название новой категории:", reply_markup=admin_cancel_kb())
    await callback.answer()


@router.message(AdminCategoryStates.waiting_name, F.text == "⬅️ Назад")
async def cat_new_cancel(message: Message, session: AsyncSession, state: FSMContext):
    await _back_to_categories(message, session, state)


@router.message(AdminCategoryStates.waiting_name)
async def cat_new_save(message: Message, session: AsyncSession, state: FSMContext):
    await create_category(session, message.text.strip())
    await state.clear()
    categories = await get_all_categories(session)
    await message.answer("Категория добавлена ✅", reply_markup=admin_main_kb())
    await message.answer("Категории меню:", reply_markup=admin_categories_kb(categories))


@router.callback_query(F.data.startswith("a_cat_view:"))
async def cat_view(callback: CallbackQuery, session: AsyncSession):
    category_id = int(callback.data.split(":")[1])
    category = await get_category(session, category_id)
    if not category:
        await callback.answer("Категория не найдена", show_alert=True)
        return
    await callback.message.edit_text(
        f"Категория: <b>{category.name}</b>", parse_mode="HTML",
        reply_markup=admin_category_detail_kb(category),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("a_cat_rename:"))
async def cat_rename_start(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split(":")[1])
    await state.update_data(category_id=category_id)
    await state.set_state(AdminCategoryStates.waiting_rename)
    await callback.message.answer("Введите новое название категории:", reply_markup=admin_cancel_kb())
    await callback.answer()


@router.message(AdminCategoryStates.waiting_rename, F.text == "⬅️ Назад")
async def cat_rename_cancel(message: Message, session: AsyncSession, state: FSMContext):
    await _back_to_categories(message, session, state)


@router.message(AdminCategoryStates.waiting_rename)
async def cat_rename_save(message: Message, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    await rename_category(session, data["category_id"], message.text.strip())
    await state.clear()
    categories = await get_all_categories(session)
    await message.answer("Название обновлено ✅", reply_markup=admin_main_kb())
    await message.answer("Категории меню:", reply_markup=admin_categories_kb(categories))


@router.callback_query(F.data.startswith("a_cat_del:"))
async def cat_delete(callback: CallbackQuery, session: AsyncSession):
    category_id = int(callback.data.split(":")[1])
    await delete_category(session, category_id)
    categories = await get_all_categories(session)
    await callback.message.edit_text(
        "Категория удалена вместе со всеми блюдами.", reply_markup=admin_categories_kb(categories)
    )
    await callback.answer()


# ---------- Блюда ----------

@router.callback_query(F.data.startswith("a_items_list:"))
async def items_list(callback: CallbackQuery, session: AsyncSession):
    category_id = int(callback.data.split(":")[1])
    items = await get_items_by_category(session, category_id)
    await callback.message.edit_text(
        "Блюда категории (✅ в наличии / ⛔ нет в наличии):",
        reply_markup=admin_items_kb(items, category_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("a_item_new:"))
async def item_new_start(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split(":")[1])
    await state.update_data(category_id=category_id)
    await state.set_state(AdminItemStates.waiting_name)
    await callback.message.answer("Введите название блюда:", reply_markup=admin_cancel_kb())
    await callback.answer()


@router.message(AdminItemStates.waiting_name, F.text == "⬅️ Назад")
async def item_new_name_cancel(message: Message, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    await _back_to_items(message, session, state, data["category_id"])


@router.message(AdminItemStates.waiting_name)
async def item_new_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AdminItemStates.waiting_description)
    await message.answer(
        "Введите описание блюда (или отправьте «-», чтобы пропустить):", reply_markup=admin_cancel_kb()
    )


@router.message(AdminItemStates.waiting_description, F.text == "⬅️ Назад")
async def item_new_description_cancel(message: Message, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    await _back_to_items(message, session, state, data["category_id"])


@router.message(AdminItemStates.waiting_description)
async def item_new_description(message: Message, state: FSMContext):
    description = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(description=description)
    await state.set_state(AdminItemStates.waiting_price)
    await message.answer("Введите цену (число, например 350):", reply_markup=admin_cancel_kb())


@router.message(AdminItemStates.waiting_price, F.text == "⬅️ Назад")
async def item_new_price_cancel(message: Message, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    await _back_to_items(message, session, state, data["category_id"])


@router.message(AdminItemStates.waiting_price)
async def item_new_price(message: Message, session: AsyncSession, state: FSMContext):
    try:
        price = float(message.text.replace(",", ".").strip())
    except ValueError:
        await message.answer("Цена должна быть числом. Попробуйте ещё раз:")
        return

    data = await state.get_data()
    item = await create_item(session, data["category_id"], data["name"], data.get("description"), price)
    await state.update_data(item_id=item.id)
    await state.set_state(AdminItemStates.waiting_photo)
    await message.answer(
        "Блюдо сохранено ✅ Теперь отправьте фото, либо напишите «-», чтобы пропустить:",
        reply_markup=admin_cancel_kb(),
    )


@router.message(AdminItemStates.waiting_photo, F.photo)
async def item_new_photo(message: Message, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    photo_file_id = message.photo[-1].file_id
    await update_item_photo(session, data["item_id"], photo_file_id)
    await state.clear()
    items = await get_items_by_category(session, data["category_id"])
    await message.answer("Фото добавлено ✅", reply_markup=admin_main_kb())
    await message.answer("Блюда категории (✅ в наличии / ⛔ нет в наличии):",
                          reply_markup=admin_items_kb(items, data["category_id"]))


@router.message(AdminItemStates.waiting_photo, F.text.in_({"-", "⬅️ Назад"}))
async def item_new_skip_photo(message: Message, session: AsyncSession, state: FSMContext):
    # Блюдо к этому шагу уже сохранено в БД (см. item_new_price), поэтому и
    # «-», и «⬅️ Назад» здесь означают одно и то же — завершить без фото.
    data = await state.get_data()
    await state.clear()
    items = await get_items_by_category(session, data["category_id"])
    await message.answer("Блюдо добавлено ✅", reply_markup=admin_main_kb())
    await message.answer("Блюда категории (✅ в наличии / ⛔ нет в наличии):",
                          reply_markup=admin_items_kb(items, data["category_id"]))


@router.message(AdminItemStates.waiting_photo)
async def item_new_photo_invalid(message: Message):
    await message.answer("Отправьте фото блюда, либо напишите «-», чтобы пропустить этот шаг.")


@router.callback_query(F.data.startswith("a_item_view:"))
async def item_view(callback: CallbackQuery, session: AsyncSession):
    item_id = int(callback.data.split(":")[1])
    item = await get_item(session, item_id)
    if not item:
        await callback.answer("Блюдо не найдено", show_alert=True)
        return
    await _show_item_card(callback, item)
    await callback.answer()


@router.callback_query(F.data.startswith("a_item_toggle:"))
async def item_toggle(callback: CallbackQuery, session: AsyncSession):
    item_id = int(callback.data.split(":")[1])
    item = await get_item(session, item_id)
    if not item:
        await callback.answer("Блюдо не найдено", show_alert=True)
        return
    await update_item_availability(session, item_id, not item.is_available)
    item = await get_item(session, item_id)
    await _show_item_card(callback, item, replace=True)
    await callback.answer("Статус обновлён — клиенты сразу увидят изменение")


@router.callback_query(F.data.startswith("a_item_del:"))
async def item_delete(callback: CallbackQuery, session: AsyncSession):
    item_id = int(callback.data.split(":")[1])
    item = await get_item(session, item_id)
    category_id = item.category_id if item else None
    await delete_item(session, item_id)
    if category_id:
        items = await get_items_by_category(session, category_id)
        await callback.message.edit_text("Блюдо удалено.", reply_markup=admin_items_kb(items, category_id))
    await callback.answer()


@router.callback_query(F.data.startswith("a_item_edit:"))
async def item_edit_start(callback: CallbackQuery, state: FSMContext):
    _, item_id, field = callback.data.split(":")
    await state.update_data(item_id=int(item_id), field=field)
    await state.set_state(AdminItemStates.waiting_edit_value)
    prompts = {
        "name": "Введите новое название:",
        "price": "Введите новую цену:",
        "description": "Введите новое описание (или «-», чтобы убрать описание):",
        "photo": "Отправьте новое фото:",
    }
    await callback.message.answer(prompts[field], reply_markup=admin_cancel_kb())
    await callback.answer()


@router.message(AdminItemStates.waiting_edit_value, F.text == "⬅️ Назад")
async def item_edit_cancel(message: Message, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    await _back_to_item_card(message, session, state, data["item_id"])


@router.message(AdminItemStates.waiting_edit_value, F.photo)
async def item_edit_photo_value(message: Message, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    if data.get("field") != "photo":
        return
    await update_item_photo(session, data["item_id"], message.photo[-1].file_id)
    await state.clear()
    item = await get_item(session, data["item_id"])
    await message.answer("Фото обновлено ✅", reply_markup=admin_main_kb())
    await _show_item_card(message, item)


@router.message(AdminItemStates.waiting_edit_value)
async def item_edit_value(message: Message, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    field = data["field"]
    if field == "photo":
        await message.answer("Пожалуйста, отправьте именно фото.")
        return
    if field == "price":
        try:
            value = float(message.text.replace(",", ".").strip())
        except ValueError:
            await message.answer("Цена должна быть числом. Попробуйте ещё раз:")
            return
        await update_item_fields(session, data["item_id"], price=value)
    elif field == "description":
        value = None if message.text.strip() == "-" else message.text.strip()
        await update_item_fields(session, data["item_id"], description=value)
    else:
        await update_item_fields(session, data["item_id"], **{field: message.text.strip()})
    await state.clear()
    item = await get_item(session, data["item_id"])
    await message.answer("Изменения сохранены ✅", reply_markup=admin_main_kb())
    await _show_item_card(message, item)
