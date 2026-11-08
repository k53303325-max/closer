from aiogram import F, Router
from aiogram.types import CallbackQuery

from closer.bot.handlers.stage1_common import edit_or_answer_menu, send_help, send_soon

router = Router()


@router.callback_query(F.data.in_({"menu:compose", "menu:my", "menu:profile"}))
async def menu_soon(callback: CallbackQuery) -> None:
    if callback.message:
        await send_soon(callback.message)
    await callback.answer()


@router.callback_query(F.data == "menu:help")
async def menu_help(callback: CallbackQuery) -> None:
    if callback.message:
        await send_help(callback.message)
    await callback.answer()


@router.callback_query(F.data == "menu:home")
async def menu_home(callback: CallbackQuery) -> None:
    await edit_or_answer_menu(callback)
