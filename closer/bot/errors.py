from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import ErrorEvent

from closer.texts import t

logger = logging.getLogger(__name__)
router = Router()


@router.errors()
async def on_error(event: ErrorEvent) -> bool:
    logger.exception("handler error: %s", event.exception)
    update = event.update
    if update.message:
        try:
            await update.message.answer(t("bot.error_generic"))
        except Exception:
            logger.exception("failed to send error reply")
    elif update.callback_query and update.callback_query.message:
        try:
            await update.callback_query.message.answer(t("bot.error_generic"))
            await update.callback_query.answer()
        except Exception:
            logger.exception("failed to send error reply for callback")
    return True
