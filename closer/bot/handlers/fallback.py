from aiogram import F, Router
from aiogram.types import Message

from closer.bot.handlers.stage1_common import send_use_menu

router = Router()


@router.message(F.text.regexp(r"^/\S+"))
async def unknown_command(message: Message) -> None:
    raw = (message.text or "").split()[0].lstrip("/").split("@", 1)[0].lower()
    if raw == "start":
        return
    await send_use_menu(message)


@router.message(F.text)
async def other_text(message: Message) -> None:
    await send_use_menu(message)
