from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from closer.texts import t

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(t("start.welcome"))
