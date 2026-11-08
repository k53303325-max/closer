from aiogram.types import CallbackQuery, Message

from closer.bot.keyboards_stage1 import back_home_keyboard, main_menu_keyboard
from closer.texts import t


async def send_main_menu(message: Message) -> None:
    await message.answer(t("start.welcome"), reply_markup=main_menu_keyboard())


async def send_soon(message: Message) -> None:
    await message.answer(t("bot.soon"), reply_markup=back_home_keyboard())


async def send_help(message: Message) -> None:
    await message.answer(t("help.text"), reply_markup=back_home_keyboard())


async def send_use_menu(message: Message) -> None:
    await message.answer(t("bot.use_menu"), reply_markup=main_menu_keyboard())


async def edit_or_answer_menu(callback: CallbackQuery) -> None:
    text = t("start.welcome")
    markup = main_menu_keyboard()
    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=markup)
        except Exception:
            await callback.message.answer(text, reply_markup=markup)
    await callback.answer()
