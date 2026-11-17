from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from closer.bot.compose_keyboards import with_cancel
from closer.bot.keyboards_stage1 import back_home_keyboard
from closer.texts import t


def send_invite_card_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("menu.home"), callback_data="menu:home")],
        ]
    )


def invite_preview_keyboard() -> InlineKeyboardMarkup:
    return with_cancel(
        [
            [InlineKeyboardButton(text=t("stage3.invite.view_btn"), callback_data="invite:view")],
            [InlineKeyboardButton(text=t("stage3.invite.decline_btn"), callback_data="invite:decline")],
        ]
    )


def _sign_row(doc_id: int, action: str, label_key: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=t(label_key), callback_data=f"sign:{action}:{doc_id}")


def sign_confirm_keyboard(doc_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_sign_row(doc_id, "begin", "stage3.sign.btn")],
            [_sign_row(doc_id, "send_code", "stage3.sign.code_btn")],
            [InlineKeyboardButton(text=t("menu.home"), callback_data="menu:home")],
        ]
    )


def review_keyboard(doc_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_sign_row(doc_id, "begin", "stage3.sign.btn")],
            [InlineKeyboardButton(text=t("stage3.change.btn"), callback_data=f"change:pick:{doc_id}")],
            [InlineKeyboardButton(text=t("stage3.invite.decline_btn"), callback_data="invite:decline")],
            [InlineKeyboardButton(text=t("menu.home"), callback_data="menu:home")],
        ]
    )


def change_fields_keyboard(doc_id: int) -> InlineKeyboardMarkup:
    fields = ("services", "term", "price", "payment")
    rows = [
        [InlineKeyboardButton(text=t(f"compose.edit.{f}"), callback_data=f"change:field:{doc_id}:{f}")]
        for f in fields
    ]
    rows.append([InlineKeyboardButton(text=t("menu.home"), callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def change_decision_keyboard(doc_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("stage3.change.accept"), callback_data=f"change:accept:{doc_id}"),
                InlineKeyboardButton(text=t("stage3.change.reject"), callback_data=f"change:reject:{doc_id}"),
            ],
            [InlineKeyboardButton(text=t("menu.home"), callback_data="menu:home")],
        ]
    )


def verify_prompt_keyboard() -> InlineKeyboardMarkup:
    return back_home_keyboard()