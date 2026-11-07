from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from closer.bot.keyboards import main_menu_keyboard
from closer.config import get_settings
from closer.db.models import Profile
from closer.services.users import get_or_create_user
from closer.texts import t

router = Router()


async def send_main_menu(message: Message) -> None:
    await message.answer(t("menu.ready"), reply_markup=main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(t("help.text"))


@router.message(Command("my"))
@router.callback_query(F.data == "menu:my")
async def cmd_my(event: Message | CallbackQuery, session) -> None:
    target = event.message if isinstance(event, CallbackQuery) else event
    await target.answer(t("menu.my_stub"))
    if isinstance(event, CallbackQuery):
        await event.answer()


@router.message(Command("new"))
@router.callback_query(F.data == "menu:new")
async def cmd_new(event: Message | CallbackQuery, session) -> None:
    target = event.message if isinstance(event, CallbackQuery) else event
    await target.answer(t("menu.new_stage2"))
    if isinstance(event, CallbackQuery):
        await event.answer()


@router.message(Command("profile"))
@router.callback_query(F.data == "menu:profile")
async def cmd_profile(event: Message | CallbackQuery, session) -> None:
    msg = event if isinstance(event, Message) else event.message
    user = await get_or_create_user(
        session,
        tg_user_id=event.from_user.id,
        tg_username=event.from_user.username,
    )
    profile = await session.scalar(select(Profile).where(Profile.user_id == user.id))
    if not profile or not profile.is_complete:
        await msg.answer(t("profile.not_ready"))
    else:
        phone = user.phone or "—"
        if len(phone) > 6:
            phone = phone[:4] + "•" * 4 + phone[-2:]
        await msg.answer(
            t(
                "profile.summary",
                status=profile.status or "—",
                full_name=profile.full_name or "—",
                phone=phone,
            )
        )
    if isinstance(event, CallbackQuery):
        await event.answer()


@router.message(Command("verify"))
async def cmd_verify(message: Message) -> None:
    await message.answer(t("verify.stub"))


@router.callback_query(F.data == "menu:pay")
async def pay_stub(cb: CallbackQuery) -> None:
    settings = get_settings()
    await cb.message.answer(t("billing.soon", price=settings.contract_price_rub))
    await cb.answer()
