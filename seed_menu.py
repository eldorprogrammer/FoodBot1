"""
Скрипт для заполнения базы данных меню заведения.

Создаёт категории и блюда (если их ещё нет — скрипт безопасно
перезапускать, дубликаты по названию не создаются).

Запуск:
    python seed_menu.py
"""

import asyncio

from sqlalchemy import select

from database.crud import create_category, create_item
from database.engine import async_session, init_db
from database.models import Category, MenuItem

# category name -> list of (item name, price)
MENU: dict[str, list[tuple[str, float]]] = {
    "🥗 Салаты": [
        ("Греческий", 8),
        ("Цезарь с курицей", 10),
        ("Цезарь с креветками", 13),
        ("Овощной салат", 7),
        ("Ачичук", 6),
        ("Шакароб", 6),
        ("Теплый салат с говядиной", 12),
        ("Салат с тунцом", 12),
        ("Капрезе", 11),
        ("Оливье", 8),
    ],
    "🍲 Супы": [
        ("Шурпа", 10),
        ("Лагман", 11),
        ("Мастава", 9),
        ("Чучвара", 10),
        ("Борщ", 9),
        ("Крем-суп грибной", 9),
        ("Куриный суп", 8),
        ("Чечевичный суп", 8),
    ],
    "🍛 Восточные блюда": [
        ("Узбекский плов", 14),
        ("Казан-кебаб", 18),
        ("Манты (5 шт.)", 12),
        ("Самса (2 шт.)", 7),
        ("Долма", 13),
        ("Жареный лагман", 13),
        ("Бешбармак", 18),
        ("Говурма", 16),
    ],
    "🍝 Европейские блюда": [
        ("Паста Карбонара", 14),
        ("Паста Болоньезе", 14),
        ("Лазанья", 16),
        ("Стейк из говядины", 28),
        ("Курица в сливочном соусе", 16),
        ("Рыба на гриле", 22),
        ("Ризотто с грибами", 15),
        ("Шницель", 17),
    ],
    "🔥 Барбекю и мангал": [
        ("Шашлык из баранины", 16),
        ("Шашлык из говядины", 15),
        ("Шашлык из курицы", 12),
        ("Люля-кебаб", 13),
        ("Куриные крылышки BBQ", 12),
        ("Стейк из семги", 24),
        ("Овощи на гриле", 10),
        ("Ассорти шашлыков", 40),
    ],
    "🍰 Десерты": [
        ("Чизкейк", 8),
        ("Медовик", 7),
        ("Наполеон", 7),
        ("Тирамису", 8),
        ("Шоколадный фондан", 9),
        ("Мороженое", 6),
        ("Фруктовая тарелка", 12),
    ],
    "🥤 Напитки (безалкогольные)": [
        ("Вода 0.5 л", 2),
        ("Coca-Cola 0.33 л", 3),
        ("Fanta", 3),
        ("Sprite", 3),
        ("Сок", 4),
        ("Лимонад", 5),
        ("Айран", 3),
        ("Морс", 4),
    ],
    "☕ Горячие напитки": [
        ("Эспрессо", 3),
        ("Американо", 4),
        ("Капучино", 5),
        ("Латте", 5),
        ("Черный чай", 3),
        ("Зеленый чай", 3),
        ("Чайник чая", 7),
    ],
}


async def seed() -> None:
    await init_db()

    async with async_session() as session:
        # уже существующие категории (по названию), чтобы не плодить дубликаты
        result = await session.execute(select(Category))
        existing_categories = {c.name: c for c in result.scalars().all()}

        for sort_order, (category_name, items) in enumerate(MENU.items()):
            category = existing_categories.get(category_name)
            if category is None:
                category = await create_category(session, category_name)
                category.sort_order = sort_order
                await session.commit()
                print(f"+ категория: {category_name}")
            else:
                print(f"= категория уже есть: {category_name}")

            result = await session.execute(
                select(MenuItem).where(MenuItem.category_id == category.id)
            )
            existing_items = {i.name for i in result.scalars().all()}

            for item_name, price in items:
                if item_name in existing_items:
                    print(f"    = блюдо уже есть: {item_name}")
                    continue
                await create_item(session, category.id, item_name, None, price)
                print(f"    + блюдо: {item_name} — ${price}")

    print("\nГотово.")


if __name__ == "__main__":
    asyncio.run(seed())
