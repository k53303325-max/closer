from aiogram import F, Router
from aiogram.types import Message

from closer.texts import t

router = Router()
_KNOWN = frozenset({"start", "help", "new", "my", "profile"})


@router.message(F.text & ~F.text.startswith("/"))
async def other_text(message: Message) -> None:
    await message.answer(t("bot.unknown_message"))


@router.message(F.text.regexp(r"^/\S+"))
async def unknown_command(message: Message) -> None:
    raw = (message.text or "").split()[0].lstrip("/").split("@", 1)[0].lower()
    if raw in _KNOWN:
        return
    await message.answer(t("bot.unknown_message"))
