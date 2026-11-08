from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Update

from closer.bot.stage1_polling import build_stage1_bot, build_stage1_dispatcher
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

    _bot = build_stage1_bot(settings.bot_token)
    _dp = build_stage1_dispatcher()
    logger.info("Stage-1 dispatcher initialized")
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
