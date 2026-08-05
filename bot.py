import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database.engine import init_db
from middlewares.db import DbSessionMiddleware

from handlers.user import start as user_start
from handlers.user import menu as user_menu
from handlers.user import cart as user_cart
from handlers.user import checkout as user_checkout
from handlers.user import history as user_history
from handlers.user import fallback as user_fallback

from handlers.admin import auth as admin_auth
from handlers.admin import entry as admin_entry
from handlers.admin import menu_management as admin_menu
from handlers.admin import orders_management as admin_orders
from handlers.admin import stats as admin_stats


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    await init_db()

    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DbSessionMiddleware())

    # Порядок важен: админские роутеры регистрируем первыми, чтобы команды
    # вроде /admin и кнопки админ-панели не перехватывались пользовательскими хендлерами.
    # admin_auth — без фильтра IsAdmin, доступен любому посетителю (это и есть
    # отдельный вход по логину/паролю через кнопку "🔐 Админ-панель").
    dp.include_router(admin_auth.router)
    dp.include_router(admin_entry.router)
    dp.include_router(admin_menu.router)
    dp.include_router(admin_orders.router)
    dp.include_router(admin_stats.router)

    dp.include_router(user_start.router)
    dp.include_router(user_menu.router)
    dp.include_router(user_cart.router)
    dp.include_router(user_checkout.router)
    dp.include_router(user_history.router)
    dp.include_router(user_fallback.router)  # обязательно последним

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
