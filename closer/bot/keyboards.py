from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from closer.texts import t


def consent_keyboard(checked: bool) -> InlineKeyboardMarkup:
    mark = "☑" if checked else "☐"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("pep.toggle", mark=mark), callback_data="pep:toggle")],
            [InlineKeyboardButton(text=t("pep.continue_btn"), callback_data="pep:continue")],
        ]
    )


def contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("contact.share_btn"), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[]], resize_keyboard=True)


def status_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("profile.status.individual"), callback_data="prof:st:individual")],
            [InlineKeyboardButton(text=t("profile.status.self_employed"), callback_data="prof:st:self_employed")],
            [InlineKeyboardButton(text=t("profile.status.ip"), callback_data="prof:st:ip")],
            [InlineKeyboardButton(text=t("profile.status.ooo"), callback_data="prof:st:ooo")],
        ]
    )


def vat_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("profile.vat.none"), callback_data="prof:vat:none")],
            [InlineKeyboardButton(text=t("profile.vat.vat22"), callback_data="prof:vat:vat22")],
            [InlineKeyboardButton(text=t("profile.vat.vat7"), callback_data="prof:vat:vat7")],
            [InlineKeyboardButton(text=t("profile.vat.vat5"), callback_data="prof:vat:vat5")],
        ]
    )


def signer_basis_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("profile.basis.charter"), callback_data="prof:basis:Устава")],
            [InlineKeyboardButton(text=t("profile.basis.poa"), callback_data="prof:basis:доверенности")],
        ]
    )


def skip_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t("common.skip"), callback_data="prof:skip")]]
    )


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("menu.new"), callback_data="menu:new")],
            [InlineKeyboardButton(text=t("menu.my"), callback_data="menu:my")],
            [InlineKeyboardButton(text=t("menu.profile"), callback_data="menu:profile")],
        ]
    )
