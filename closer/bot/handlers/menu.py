from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from closer.texts import t

router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(t("help.text"))


@router.message(Command("new"))
async def cmd_new(message: Message) -> None:
    await message.answer(t("bot.soon"))


@router.message(Command("my"))
async def cmd_my(message: Message) -> None:
    await message.answer(t("bot.soon"))


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    await message.answer(t("bot.soon"))
