from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from closer.texts import t


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("menu.compose"), callback_data="menu:compose")],
            [
                InlineKeyboardButton(text=t("menu.my"), callback_data="menu:my"),
                InlineKeyboardButton(text=t("menu.profile"), callback_data="menu:profile"),
            ],
            [InlineKeyboardButton(text=t("menu.help"), callback_data="menu:help")],
        ]
    )


def back_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("menu.home"), callback_data="menu:home")],
        ]
    )
