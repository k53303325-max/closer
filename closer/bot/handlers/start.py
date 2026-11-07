import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from closer.bot.handlers.onboarding import resume_or_pep
from closer.texts import t

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await message.answer(t("start.welcome"))
    try:
        await resume_or_pep(message, state, session)
    except Exception:
        logger.exception("/start onboarding failed for tg_user_id=%s", message.from_user.id)
        await message.answer(t("common.error_generic"))
        raise
