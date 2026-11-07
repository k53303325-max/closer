import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand

from closer.bot.errors import router as errors_router
from closer.bot.handlers.menu import router as menu_router
from closer.bot.handlers.onboarding import router as onboarding_router
from closer.bot.handlers.start import router as start_router
from closer.bot.middlewares import DbSessionMiddleware
from closer.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COMMANDS = [
    BotCommand(command="start", description="Начать"),
    BotCommand(command="new", description="Новый договор"),
    BotCommand(command="my", description="Мои договоры"),
    BotCommand(command="profile", description="Мой профиль"),
    BotCommand(command="verify", description="Проверить подлинность PDF"),
    BotCommand(command="help", description="Помощь"),
]


async def main() -> None:
    settings = get_settings()
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN is required")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        storage = RedisStorage.from_url(settings.redis_url)
    except Exception:
        logger.exception("Redis unavailable at %s", settings.redis_url)
        raise SystemExit("REDIS_URL is required for FSM (start redis service)") from None

    dp = Dispatcher(storage=storage)
    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(errors_router)
    dp.include_router(start_router)
    dp.include_router(onboarding_router)
    dp.include_router(menu_router)

    me = await bot.get_me()
    logger.info("Bot @%s is starting (polling)", me.username)
    await bot.set_my_commands(COMMANDS)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
