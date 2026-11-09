from __future__ import annotations

from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.enums import ContentType
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from closer.bot.keyboards import (
    consent_keyboard,
    contact_keyboard,
    remove_keyboard,
    signer_basis_keyboard,
    skip_keyboard,
    status_keyboard,
    vat_keyboard,
)
from closer.bot.states import OnboardingStates, ProfileStates
from closer.config import get_settings
from closer.db.models import Consent
from closer.documents.parties import IP, OOO
from closer.services.audit import append_audit
from closer.services.pep import load_pep_offer
from closer.services.profile import draft_missing_for_status, get_cipher, load_draft_from_db, profile_is_complete, save_profile
from closer.services.profile_fields import ProfileDraft, draft_from_dict
from closer.services.users import get_or_create_user, save_phone, user_has_pep_consent
from closer.services.validation import (
    validate_inn,
    validate_ogrn,
    validate_ogrnip,
    validate_passport,
)
from closer.texts import t

router = Router()


async def send_pep_prompt(message: Message, state: FSMContext) -> None:
    offer = load_pep_offer()
    settings = get_settings()
    data = await state.get_data()
    await state.set_state(OnboardingStates.pep)
    await state.update_data(pep_checked=False)
    text = t(
        "pep.intro",
        summary=offer.summary,
        pep_version=offer.version,
        pd_url=settings.pd_policy_url,
    )
    await message.answer(
        text,
        reply_markup=consent_keyboard(False, show_cancel=data.get("flow") == "compose"),
    )
    doc = FSInputFile(settings.pep_offer_path, filename="pep_offer.md")
    await message.answer_document(doc, caption=t("pep.full_doc_caption"))


@router.callback_query(StateFilter(OnboardingStates.pep), F.data == "pep:toggle")
async def pep_toggle(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    checked = not bool(data.get("pep_checked"))
    await state.update_data(pep_checked=checked)
    await cb.message.edit_reply_markup(
        reply_markup=consent_keyboard(checked, show_cancel=data.get("flow") == "compose")
    )
    await cb.answer()


@router.callback_query(StateFilter(OnboardingStates.pep), F.data == "pep:continue")
async def pep_continue(cb: CallbackQuery, state: FSMContext, session) -> None:
    data = await state.get_data()
    if not data.get("pep_checked"):
        await cb.answer(t("pep.must_check"), show_alert=True)
        return

    user = await get_or_create_user(
        session,
        tg_user_id=cb.from_user.id,
        tg_username=cb.from_user.username,
    )
    offer = load_pep_offer()
    settings = get_settings()
    now = datetime.now(UTC)
    for kind in ("pep_offer", "pd_policy"):
        session.add(
            Consent(
                user_id=user.id,
                kind=kind,
                doc_version=offer.version if kind == "pep_offer" else "pd_policy_v0",
                doc_sha256=offer.sha256 if kind == "pep_offer" else "0" * 64,
                accepted_at=now,
            )
        )
    await append_audit(
        session,
        event="offer_accepted",
        actor_user_id=user.id,
        payload={
            "tg_user_id": cb.from_user.id,
            "tg_username": cb.from_user.username,
            "pep_version": offer.version,
            "pd_policy_url": settings.pd_policy_url,
        },
        doc_sha256=offer.sha256,
        pep_version=offer.version,
    )
    flow = data.get("flow")
    if flow == "compose" and user.phone:
        from closer.bot.handlers.compose import compose_skip_contact_to_role

        await compose_skip_contact_to_role(cb.message, state, session, user)
        await cb.answer()
        return
    await state.set_state(OnboardingStates.contact)
    await cb.message.answer(
        t("contact.prompt"),
        reply_markup=contact_keyboard(),
    )
    await cb.answer()


@router.message(StateFilter(OnboardingStates.contact), F.content_type == ContentType.CONTACT)
async def contact_shared(message: Message, state: FSMContext, session) -> None:
    contact = message.contact
    if not contact or not contact.phone_number:
        await message.answer(t("contact.invalid"))
        return
    if contact.user_id and contact.user_id != message.from_user.id:
        await message.answer(t("contact.not_yours"))
        return

    user = await get_or_create_user(
        session,
        tg_user_id=message.from_user.id,
        tg_username=message.from_user.username,
    )
    phone = contact.phone_number
    if not phone.startswith("+"):
        phone = f"+{phone}"
    await save_phone(session, user, phone)
    await append_audit(
        session,
        event="contact_shared",
        actor_user_id=user.id,
        payload={"phone_mask": phone[:4] + "***"},
    )

    data = await state.get_data()
    if data.get("flow") == "compose":
        from closer.bot.handlers.compose import compose_after_contact

        await compose_after_contact(message, state, session)
        return

    await state.set_state(ProfileStates.filling)
    draft = await load_draft_from_db(session, user.id)
    await state.update_data(profile=draft.__dict__)
    await message.answer(t("contact.saved"), reply_markup=remove_keyboard())
    await prompt_profile_step(message, state, draft, session)


async def prompt_profile_step(
    message: Message,
    state: FSMContext,
    draft: ProfileDraft,
    session,
) -> None:
    step = draft.next_field()
    if step is None or profile_is_complete(draft):
        data = await state.get_data()
        user_id = data.get("db_user_id")
        if user_id is not None:
            await save_profile(session, user_id, draft)
        await message.answer(t("profile.done"))
        await state.clear()
        from closer.bot.handlers.stage1_common import send_main_menu

        await send_main_menu(message)
        return

    prompts = {
        "status": ("profile.ask_status", status_keyboard()),
        "full_name": ("profile.ask_full_name", None),
        "passport": ("profile.ask_passport", None),
        "inn": ("profile.ask_inn", None),
        "ogrn": ("profile.ask_ogrn", None),
        "org_name": ("profile.ask_org_name", None),
        "signer_position": ("profile.ask_signer_position", None),
        "signer_basis": ("profile.ask_signer_basis", signer_basis_keyboard()),
        "address": ("profile.ask_address", None),
        "vat_mode": ("profile.ask_vat", vat_keyboard()),
        "email_optional": ("profile.ask_email", skip_keyboard()),
        "payout_optional": ("profile.ask_payout", skip_keyboard()),
    }
    key, markup = prompts[step]
    await message.answer(t(key), reply_markup=markup)


@router.callback_query(StateFilter(ProfileStates.filling), F.data.startswith("prof:st:"))
async def profile_status(cb: CallbackQuery, state: FSMContext, session) -> None:
    status = cb.data.split(":")[-1]
    user = await get_or_create_user(session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username)
    draft = draft_from_dict((await state.get_data()).get("profile"))
    draft.status = status
    await state.update_data(profile=draft.__dict__, db_user_id=user.id)
    await save_profile(session, user.id, draft)
    await cb.message.answer(t("profile.status_hint"))
    await prompt_profile_step(cb.message, state, draft, session)
    await cb.answer()


@router.callback_query(StateFilter(ProfileStates.filling), F.data.startswith("prof:vat:"))
async def profile_vat(cb: CallbackQuery, state: FSMContext, session) -> None:
    mode = cb.data.split(":")[-1]
    data = await state.get_data()
    draft = draft_from_dict(data.get("profile"))
    draft.vat_mode = mode
    user = await get_or_create_user(session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username)
    await save_profile(session, user.id, draft)
    await state.update_data(profile=draft.__dict__)
    await prompt_profile_step(cb.message, state, draft, session)
    await cb.answer()


@router.callback_query(StateFilter(ProfileStates.filling), F.data.startswith("prof:basis:"))
async def profile_basis(cb: CallbackQuery, state: FSMContext, session) -> None:
    basis = cb.data.split(":", 2)[-1]
    data = await state.get_data()
    draft = draft_from_dict(data.get("profile"))
    draft.signer_basis = basis
    user = await get_or_create_user(session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username)
    await save_profile(session, user.id, draft)
    await state.update_data(profile=draft.__dict__)
    await prompt_profile_step(cb.message, state, draft, session)
    await cb.answer()


@router.callback_query(StateFilter(ProfileStates.filling), F.data == "prof:skip")
async def profile_skip(cb: CallbackQuery, state: FSMContext, session) -> None:
    data = await state.get_data()
    draft = draft_from_dict(data.get("profile"))
    step = draft.next_field()
    if step == "email_optional":
        draft.email = ""
    elif step == "payout_optional":
        draft.bank = ""
        draft.sbp = ""
    user = await get_or_create_user(session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username)
    await save_profile(session, user.id, draft)
    await state.update_data(profile=draft.__dict__)
    await prompt_profile_step(cb.message, state, draft, session)
    await cb.answer()


@router.message(StateFilter(ProfileStates.filling), F.text)
async def profile_text(message: Message, state: FSMContext, session) -> None:
    _ = get_cipher()  # fail fast if key missing
    user = await get_or_create_user(
        session,
        tg_user_id=message.from_user.id,
        tg_username=message.from_user.username,
    )
    data = await state.get_data()
    draft = draft_from_dict(data.get("profile"))
    step = draft.next_field()
    if step in (None, "status", "vat_mode", "signer_basis"):
        await message.answer(t("profile.use_buttons"))
        return

    text = (message.text or "").strip()
    validators = {
        "passport": (validate_passport, "profile.errors.passport"),
        "inn": (validate_inn, "profile.errors.inn"),
        "ogrn": (
            (lambda v: validate_ogrn(v) if draft.status == OOO else validate_ogrnip(v)),
            "profile.errors.ogrn",
        ),
    }
    if step in validators:
        fn, err = validators[step]
        if not fn(text):
            await message.answer(t(err))
            return

    field_map = {
        "full_name": "full_name",
        "passport": "passport",
        "inn": "inn",
        "ogrn": "ogrn",
        "org_name": "org_name",
        "signer_position": "signer_position",
        "address": "address",
        "email_optional": "email",
        "payout_optional": "bank",
    }
    attr = field_map[step]
    if step == "payout_optional":
        if "@" in text or "." in text:
            draft.bank = text
        else:
            draft.sbp = text
    else:
        setattr(draft, attr, text)

    if draft_missing_for_status(draft) and step not in ("email_optional", "payout_optional"):
        await message.answer(t("profile.errors.required_fields"))
        return

    await save_profile(session, user.id, draft)
    await state.update_data(profile=draft.__dict__, db_user_id=user.id)
    if draft.status in (IP, OOO) and step == "address" and draft.vat_mode == "none":
        pass
    await prompt_profile_step(message, state, draft, session)


async def resume_or_pep(message: Message, state: FSMContext, session) -> None:
    user = await get_or_create_user(
        session,
        tg_user_id=message.from_user.id,
        tg_username=message.from_user.username,
    )
    settings = get_settings()
    if not await user_has_pep_consent(session, user.id, settings.pep_offer_version):
        await send_pep_prompt(message, state)
        return
    if not user.phone:
        await state.set_state(OnboardingStates.contact)
        await message.answer(t("contact.prompt"), reply_markup=contact_keyboard())
        return
    profile = await load_draft_from_db(session, user.id)
    if not profile_is_complete(profile):
        await state.set_state(ProfileStates.filling)
        await state.update_data(profile=profile.__dict__, db_user_id=user.id)
        await prompt_profile_step(message, state, profile, session)
        return
    from closer.bot.handlers.stage1_common import send_main_menu

    await send_main_menu(message)
