from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from closer.bot.handlers.stage1_common import send_main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await send_main_menu(message)
