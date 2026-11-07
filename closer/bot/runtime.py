from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Update

from closer.bot.errors import router as errors_router
from closer.bot.handlers.menu import router as menu_router
from closer.bot.handlers.onboarding import router as onboarding_router
from closer.bot.handlers.start import router as start_router
from closer.bot.middlewares import DbSessionMiddleware
from closer.config import get_settings

logger = logging.getLogger(__name__)

_bot: Bot | None = None
_dp: Dispatcher | None = None


def build_dispatcher() -> tuple[Bot, Dispatcher]:
    global _bot, _dp
    if _bot is not None and _dp is not None:
        return _bot, _dp

    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is required")

    _bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = RedisStorage.from_url(settings.redis_url)
    _dp = Dispatcher(storage=storage)
    _dp.update.middleware(DbSessionMiddleware())
    _dp.include_router(errors_router)
    _dp.include_router(start_router)
    _dp.include_router(onboarding_router)
    _dp.include_router(menu_router)
    logger.info("Dispatcher initialized")
    return _bot, _dp


async def process_update(data: dict) -> None:
    bot, dp = build_dispatcher()
    update = Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot, update)


async def set_webhook(base_url: str) -> str:
    bot, _ = build_dispatcher()
    url = f"{base_url.rstrip('/')}/api/telegram"
    await bot.set_webhook(url, drop_pending_updates=True)
    logger.info("Webhook set to %s", url)
    return url
