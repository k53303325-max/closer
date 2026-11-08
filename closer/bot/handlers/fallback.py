from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from closer.texts import t

router = Router()


@router.message(F.text & ~F.text.startswith("/"))
async def other_text(message: Message) -> None:
    await message.answer(t("bot.unknown_message"))


@router.message(Command())
async def unknown_command(message: Message) -> None:
    allowed = {"start", "help", "new", "my", "profile"}
    raw = (message.text or "").split()[0].lstrip("/").split("@", 1)[0].lower()
    if raw in allowed:
        return
    await message.answer(t("bot.unknown_message"))
