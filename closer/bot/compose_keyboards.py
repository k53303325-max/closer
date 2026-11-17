from __future__ import annotations

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


def profile_status_keyboard() -> InlineKeyboardMarkup:
    return with_cancel(
        [
            [InlineKeyboardButton(text=t("profile.status.individual"), callback_data="prof:st:individual")],
            [InlineKeyboardButton(text=t("profile.status.self_employed"), callback_data="prof:st:self_employed")],
            [InlineKeyboardButton(text=t("profile.status.ip"), callback_data="prof:st:ip")],
            [InlineKeyboardButton(text=t("profile.status.ooo"), callback_data="prof:st:ooo")],
        ]
    )


def profile_vat_keyboard() -> InlineKeyboardMarkup:
    return with_cancel(
        [
            [InlineKeyboardButton(text=t("profile.vat.none"), callback_data="prof:vat:none")],
            [InlineKeyboardButton(text=t("profile.vat.vat22"), callback_data="prof:vat:vat22")],
            [InlineKeyboardButton(text=t("profile.vat.vat7"), callback_data="prof:vat:vat7")],
            [InlineKeyboardButton(text=t("profile.vat.vat5"), callback_data="prof:vat:vat5")],
        ]
    )


def profile_basis_keyboard() -> InlineKeyboardMarkup:
    return with_cancel(
        [
            [InlineKeyboardButton(text=t("profile.basis.charter"), callback_data="prof:basis:Устава")],
            [InlineKeyboardButton(text=t("profile.basis.poa"), callback_data="prof:basis:доверенности")],
        ]
    )


def card_keyboard(document_id: int | None = None) -> InlineKeyboardMarkup:
    send_data = f"compose:card:send:{document_id}" if document_id else "compose:card:send"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("compose.card.edit"), callback_data="compose:card:edit")],
            [InlineKeyboardButton(text=t("stage3.send.btn"), callback_data=send_data)],
            [InlineKeyboardButton(text=t("compose:card.delete"), callback_data="compose:card:delete")],
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
                InlineKeyboardButton(text=t("compose.delete.confirm_yes"), callback_data="compose:delete:yes"),
                InlineKeyboardButton(text=t("compose.delete.confirm_no"), callback_data="compose:delete:no"),
            ],
        ]
    )