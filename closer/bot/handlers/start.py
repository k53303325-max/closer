from aiogram import Bot, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from closer.bot.handlers.stage1_common import send_main_menu
from closer.bot.handlers.stage3 import handle_invite_deep_link
from closer.services.invites import INVITE_PREFIX

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session, bot: Bot) -> None:
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) > 1 and parts[1].startswith(INVITE_PREFIX):
        if await handle_invite_deep_link(message, state, session, bot, parts[1]):
            return
    await send_main_menu(message)