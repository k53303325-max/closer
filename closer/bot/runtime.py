from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Update

from closer.bot.stage1_polling import build_stage1_bot, build_stage1_dispatcher
from closer.config import get_settings
from closer.db.init_db import ensure_schema
from closer.db.session import _engine

logger = logging.getLogger(__name__)

_bot: Bot | None = None
_dp: Dispatcher | None = None
_schema_ready = False


def build_dispatcher() -> tuple[Bot, Dispatcher]:
    global _bot, _dp
    if _bot is not None and _dp is not None:
        return _bot, _dp

    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is required")

    _bot = build_stage1_bot(settings.bot_token)
    _dp = build_stage1_dispatcher()
    logger.info("Dispatcher initialized (stages 1–3)")
    return _bot, _dp


async def process_update(data: dict) -> None:
    global _schema_ready
    bot, dp = build_dispatcher()
    if not _schema_ready:
        await ensure_schema(_engine)
        _schema_ready = True
    update = Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot, update)


async def set_webhook(base_url: str) -> str:
    bot, _ = build_dispatcher()
    url = f"{base_url.rstrip('/')}/api/telegram"
    await bot.set_webhook(url, drop_pending_updates=True)
    logger.info("Webhook set to %s", url)
    return url
