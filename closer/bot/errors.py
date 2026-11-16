from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import ErrorEvent

from closer.texts import t

logger = logging.getLogger(__name__)
router = Router()


def _db_error(exc: BaseException) -> bool:
    if isinstance(exc, ConnectionRefusedError):
        return True
    cause = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
    if isinstance(cause, ConnectionRefusedError):
        return True
    msg = str(exc).lower()
    return "connection refused" in msg or "connect call failed" in msg


@router.errors()
async def on_error(event: ErrorEvent) -> bool:
    logger.exception("handler error: %s", event.exception)
    update = event.update
    text = t("bot.db_unavailable") if _db_error(event.exception) else t("bot.error_generic")
    if update.message:
        try:
            await update.message.answer(text)
        except Exception:
            logger.exception("failed to send error reply")
    elif update.callback_query and update.callback_query.message:
        try:
            await update.callback_query.message.answer(text)
            await update.callback_query.answer()
        except Exception:
            logger.exception("failed to send error reply for callback")
    return True
