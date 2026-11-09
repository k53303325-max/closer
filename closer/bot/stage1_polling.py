"""Shared stage-1 handlers (polling + optional webhook)."""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from closer.bot.errors import router as errors_router
from closer.bot.handlers.compose import router as compose_router
from closer.bot.handlers.fallback import router as fallback_router
from closer.bot.handlers.menu import router as menu_router
from closer.bot.handlers.onboarding import router as onboarding_router
from closer.bot.handlers.start import router as start_router
from closer.bot.middlewares import DbSessionMiddleware
from closer.texts import t


def build_stage1_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(errors_router)
    dp.include_router(start_router)
    dp.include_router(compose_router)
    dp.include_router(onboarding_router)
    dp.include_router(menu_router)
    dp.include_router(fallback_router)
    return dp


def bot_commands() -> list[BotCommand]:
    return [BotCommand(command="start", description=t("bot.commands.start"))]


def build_stage1_bot(token: str) -> Bot:
    return Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
