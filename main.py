import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from db import init_db
from middlewares.anti_spam import AntiSpamMiddleware
from middlewares.ban_check import BanCheckMiddleware
from handlers import start, admin, application, support, messages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Инициализация базы данных...")
    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())

    # ── Middlewares (порядок важен) ────────────────────────────────────────
    dp.message.middleware(BanCheckMiddleware())
    dp.callback_query.middleware(BanCheckMiddleware())
    dp.message.middleware(AntiSpamMiddleware())

    # ── Routers (порядок важен: admin до messages) ─────────────────────────
    # start.router зарегистрирован первым — его "❌ Отменить" имеет приоритет
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(application.router)
    dp.include_router(support.router)
    dp.include_router(messages.router)  # catch-all в конце

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот запущен. Ожидание сообщений...")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
