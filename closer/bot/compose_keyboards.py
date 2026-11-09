from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from closer.services.fields_schema import PAYMENT_UI
from closer.texts import t


def with_cancel(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    rows = list(rows)
    rows.append([InlineKeyboardButton(text=t("compose.cancel"), callback_data="compose:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def resume_keyboard() -> InlineKeyboardMarkup:
    return with_cancel(
        [
            [InlineKeyboardButton(text=t("compose.resume_continue"), callback_data="compose:resume:continue")],
            [InlineKeyboardButton(text=t("compose.resume_new"), callback_data="compose:resume:new")],
        ]
    )


def role_keyboard() -> InlineKeyboardMarkup:
    return with_cancel(
        [
            [
                InlineKeyboardButton(text=t("compose.role.executor"), callback_data="compose:role:executor"),
                InlineKeyboardButton(text=t("compose.role.customer"), callback_data="compose:role:customer"),
            ],
        ]
    )


def payment_keyboard() -> InlineKeyboardMarkup:
    return with_cancel(
        [
            [InlineKeyboardButton(text=PAYMENT_UI["prepay"], callback_data="compose:pay:prepay")],
            [InlineKeyboardButton(text=PAYMENT_UI["postpay"], callback_data="compose:pay:postpay")],
            [InlineKeyboardButton(text=PAYMENT_UI["split"], callback_data="compose:pay:split")],
        ]
    )


def card_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("compose.card.edit"), callback_data="compose:card:edit")],
            [InlineKeyboardButton(text=t("compose.card.sign"), callback_data="compose:card:sign")],
            [InlineKeyboardButton(text=t("compose.card.delete"), callback_data="compose:card:delete")],
            [InlineKeyboardButton(text=t("menu.home"), callback_data="menu:home")],
        ]
    )


def edit_fields_keyboard() -> InlineKeyboardMarkup:
    return with_cancel(
        [
            [InlineKeyboardButton(text=t("compose.edit.services"), callback_data="compose:edit:services")],
            [InlineKeyboardButton(text=t("compose.edit.term"), callback_data="compose:edit:term")],
            [InlineKeyboardButton(text=t("compose.edit.price"), callback_data="compose:edit:price")],
            [InlineKeyboardButton(text=t("compose.edit.payment"), callback_data="compose:edit:payment")],
            [InlineKeyboardButton(text=t("compose.edit.profile"), callback_data="compose:edit:profile")],
        ]
    )


def delete_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("compose.delete.yes"), callback_data="compose:delete:yes"),
                InlineKeyboardButton(text=t("compose.delete.no"), callback_data="compose:delete:no"),
            ],
        ]
    )
