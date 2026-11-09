from __future__ import annotations

import logging
from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from closer.bot.compose_keyboards import (
    card_keyboard,
    delete_confirm_keyboard,
    edit_fields_keyboard,
    payment_keyboard,
    resume_keyboard,
    role_keyboard,
    with_cancel,
)
from closer.bot.handlers.onboarding import send_pep_prompt
from closer.bot.handlers.stage1_common import send_main_menu
from closer.bot.keyboards import contact_keyboard, remove_keyboard, signer_basis_keyboard, status_keyboard, vat_keyboard
from closer.bot.states import ComposeStates, OnboardingStates
from closer.config import get_settings
from closer.documents.parties import OOO, vat_text
from closer.integrations.gigachat import get_llm_client
from closer.services.contract_build import format_card_text, party_from_draft
from closer.services.documents_service import (
    bump_free_contract_usage,
    create_composing_document,
    find_active_draft,
    find_incomplete_document,
    free_contracts_left,
    render_draft_pdf,
    save_composing_state,
    soft_delete_document,
)
from closer.services.fields_schema import DEAL_FIELD_ORDER, deal_field_prompt
from closer.services.normalize import normalize_term, parse_price
from closer.services.profile import get_cipher, load_draft_from_db, profile_ready_for_contract, save_profile
from closer.services.profile_fields import ProfileDraft, compose_profile_ready, draft_from_dict
from closer.services.users import get_or_create_user, user_has_pep_consent
from closer.services.validation import validate_inn, validate_ogrn, validate_ogrnip, validate_passport
from closer.texts import t

logger = logging.getLogger(__name__)
router = Router()


def _deal_missing_fields(deal: dict) -> list[str]:
    out = []
    for key in DEAL_FIELD_ORDER:
        if key == "payment" and not deal.get(key):
            out.append(key)
        elif key != "payment" and not deal.get(key):
            out.append(key)
    return out


async def _state_pack(state: FSMContext) -> dict[str, Any]:
    return await state.get_data()


async def _ensure_user(session, tg_user) -> tuple[Any, Any]:
    user = await get_or_create_user(session, tg_user_id=tg_user.id, tg_username=tg_user.username)
    draft = await load_draft_from_db(session, user.id)
    return user, draft


async def begin_compose(event: Message | CallbackQuery, state: FSMContext, session) -> None:
    message = event if isinstance(event, Message) else event.message
    assert message is not None
    user, _ = await _ensure_user(session, event.from_user)

    incomplete = await find_incomplete_document(session, user.id)
    if incomplete:
        await state.set_state(ComposeStates.resume_choice)
        await state.update_data(flow="compose", document_id=incomplete.id)
        await message.answer(t("compose.resume_prompt"), reply_markup=resume_keyboard())
        return

    await _start_fresh_compose(session, message, state, event.from_user)


async def _start_fresh_compose(session, message: Message, state: FSMContext, tg_user) -> None:
    user, _ = await _ensure_user(session, tg_user)
    if free_contracts_left(user) <= 0:
        await message.answer(t("billing.soon", price=get_settings().contract_price_rub))
        return
    await _gate_pep_contact(session, message, state, user)


async def _gate_pep_contact(session, message: Message, state: FSMContext, user) -> None:
    settings = get_settings()
    if not await user_has_pep_consent(session, user.id, settings.pep_offer_version):
        await state.update_data(flow="compose")
        await send_pep_prompt(message, state)
        return
    if not user.phone:
        await state.set_state(OnboardingStates.contact)
        await state.update_data(flow="compose")
        await message.answer(t("contact.prompt"), reply_markup=contact_keyboard())
        return
    await _ask_role(message, state, session, user.id)


async def compose_after_contact(message: Message, state: FSMContext, session) -> None:
    user = await get_or_create_user(session, tg_user_id=message.from_user.id, tg_username=message.from_user.username)
    await message.answer(t("contact.saved"), reply_markup=remove_keyboard())
    await _ask_role(message, state, session, user.id)


async def compose_skip_contact_to_role(message: Message, state: FSMContext, session, user) -> None:
    await state.update_data(flow="compose")
    await _ask_role(message, state, session, user.id)


async def _ask_role(message: Message, state: FSMContext, session, user_id: int) -> None:
    doc = await find_incomplete_document(session, user_id)
    if not doc:
        doc = await create_composing_document(session, user_id)
    await state.set_state(ComposeStates.role)
    await state.update_data(flow="compose", document_id=doc.id, deal=doc.deal or {})
    await message.answer(t("compose.ask_role"), reply_markup=role_keyboard())


@router.callback_query(F.data == "menu:compose")
async def menu_compose(cb: CallbackQuery, state: FSMContext, session) -> None:
    await state.clear()
    await begin_compose(cb, state, session)
    await cb.answer()


@router.callback_query(StateFilter(ComposeStates.resume_choice), F.data == "compose:resume:continue")
async def resume_continue(cb: CallbackQuery, state: FSMContext, session) -> None:
    data = await state.get_data()
    doc_id = data.get("document_id")
    user = await get_or_create_user(
        session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username
    )
    doc = await find_active_draft(session, user.id, doc_id)
    if not doc:
        await cb.message.answer(t("compose.resume_gone"))
        await begin_compose(cb, state, session)
        await cb.answer()
        return
    deal = dict(doc.deal or {})
    await state.update_data(flow="compose", document_id=doc.id, deal=deal)
    if not doc.user_role:
        await _ask_role(cb.message, state, session, user.id)
    elif _deal_missing_fields(deal):
        await state.set_state(ComposeStates.deal_text if not deal else ComposeStates.ask_field)
        if deal and _deal_missing_fields(deal):
            await _prompt_next_field(cb.message, state, session)
        else:
            await cb.message.answer(t("compose.ask_deal"))
    elif doc.status == "draft" and not _deal_missing_fields(deal):
        draft = await load_draft_from_db(session, user.id)
        await _build_card(cb.message, state, session, user, doc, draft)
    else:
        await _start_profile_or_card(cb.message, state, session, user, doc)
    await cb.answer()


@router.callback_query(StateFilter(ComposeStates.resume_choice), F.data == "compose:resume:new")
async def resume_new(cb: CallbackQuery, state: FSMContext, session) -> None:
    data = await state.get_data()
    user = await get_or_create_user(
        session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username
    )
    if data.get("document_id"):
        old = await find_active_draft(session, user.id, data["document_id"])
        if old:
            await soft_delete_document(session, old)
    await state.clear()
    await _start_fresh_compose(session, cb.message, state, cb.from_user)
    await cb.answer()


@router.callback_query(StateFilter(ComposeStates.role), F.data.startswith("compose:role:"))
async def pick_role(cb: CallbackQuery, state: FSMContext, session) -> None:
    role = cb.data.split(":")[-1]
    data = await state.get_data()
    user = await get_or_create_user(
        session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username
    )
    doc = await find_active_draft(session, user.id, data["document_id"])
    if not doc:
        await begin_compose(cb, state, session)
        await cb.answer()
        return
    doc.user_role = role
    await save_composing_state(session, doc, role=role, deal=data.get("deal") or {})
    await state.update_data(user_role=role)
    await state.set_state(ComposeStates.deal_text)
    await cb.message.answer(t("compose.ask_deal"))
    await cb.answer()


@router.message(StateFilter(ComposeStates.deal_text), F.text)
async def deal_text(message: Message, state: FSMContext, session) -> None:
    settings = get_settings()
    llm = get_llm_client(settings.gigachat_auth_key)
    extracted = await llm.classify_and_extract(message.text)
    if not extracted.get("supported", True):
        await message.answer(t("compose.unsupported_type"))
        await send_main_menu(message)
        await state.clear()
        return

    deal = (await state.get_data()).get("deal") or {}
    for key in ("services", "term", "price", "payment"):
        val = extracted.get(key)
        if val is not None and not deal.get(key):
            if key == "price" and isinstance(val, int):
                deal[key] = val
            elif key == "payment" and val:
                deal[key] = val
            elif key in ("services", "term") and val:
                if key == "term":
                    deal[key] = normalize_term(str(val))
                else:
                    deal[key] = val

    user = await get_or_create_user(
        session, tg_user_id=message.from_user.id, tg_username=message.from_user.username
    )
    doc_id = (await state.get_data()).get("document_id")
    doc = await find_active_draft(session, user.id, doc_id)
    if doc:
        await save_composing_state(session, doc, role=doc.user_role, deal=deal)
    await state.update_data(deal=deal)
    missing = _deal_missing_fields(deal)
    if missing:
        await state.set_state(ComposeStates.ask_field)
        await state.update_data(ask_field=missing[0])
        await _send_field_prompt(message, missing[0])
        return
    await _start_profile_or_card(message, state, session, user, doc)


async def _send_field_prompt(message: Message, field: str) -> None:
    if field == "payment":
        await message.answer(deal_field_prompt(field), reply_markup=payment_keyboard())
    else:
        await message.answer(deal_field_prompt(field), reply_markup=with_cancel([]))


async def _prompt_next_field(message: Message, state: FSMContext, session) -> None:
    deal = (await state.get_data()).get("deal") or {}
    missing = _deal_missing_fields(deal)
    if not missing:
        user = await get_or_create_user(
            session, tg_user_id=message.from_user.id, tg_username=message.from_user.username
        )
        doc_id = (await state.get_data()).get("document_id")
        doc = await find_active_draft(session, user.id, doc_id)
        await _start_profile_or_card(message, state, session, user, doc)
        return
    await state.set_state(ComposeStates.ask_field)
    await state.update_data(ask_field=missing[0])
    await _send_field_prompt(message, missing[0])


@router.message(StateFilter(ComposeStates.ask_field), F.text)
async def ask_field_text(message: Message, state: FSMContext, session) -> None:
    data = await state.get_data()
    field = data.get("ask_field")
    deal = dict(data.get("deal") or {})
    text = (message.text or "").strip()

    if field == "services":
        deal["services"] = text
    elif field == "term":
        deal["term"] = normalize_term(text)
    elif field == "price":
        price = parse_price(text)
        if price is None:
            await message.answer(deal_field_prompt("price"))
            return
        deal["price"] = price
    else:
        await message.answer(t("compose.use_buttons"))
        return

    await _persist_deal(session, message, state, deal)


@router.callback_query(StateFilter(ComposeStates.ask_field), F.data.startswith("compose:pay:"))
async def ask_payment(cb: CallbackQuery, state: FSMContext, session) -> None:
    key = cb.data.split(":")[-1]
    deal = dict((await state.get_data()).get("deal") or {})
    deal["payment"] = key
    await _persist_deal(cb.message, state, session, deal, cb=cb)


async def _persist_deal(
    message: Message | None,
    state: FSMContext,
    session,
    deal: dict,
    *,
    cb: CallbackQuery | None = None,
) -> None:
    assert message is not None
    tg = cb.from_user if cb else message.from_user
    user = await get_or_create_user(session, tg_user_id=tg.id, tg_username=tg.username)
    doc_id = (await state.get_data()).get("document_id")
    doc = await find_active_draft(session, user.id, doc_id)
    if doc:
        await save_composing_state(session, doc, role=doc.user_role, deal=deal)
    await state.update_data(deal=deal)
    missing = _deal_missing_fields(deal)
    if missing:
        await state.set_state(ComposeStates.ask_field)
        await state.update_data(ask_field=missing[0])
        await _send_field_prompt(message, missing[0])
    else:
        await _start_profile_or_card(message, state, session, user, doc)
    if cb:
        await cb.answer()


async def _start_profile_or_card(message: Message, state: FSMContext, session, user, doc) -> None:
    is_executor = (doc.user_role if doc else "executor") == "executor"
    draft = await load_draft_from_db(session, user.id)
    if not profile_ready_for_contract(draft, is_executor):
        await state.set_state(ComposeStates.profile)
        await state.update_data(profile=draft.__dict__, is_executor=is_executor)
        await _prompt_compose_profile(message, draft, is_executor)
        return
    await _build_card(message, state, session, user, doc, draft)


async def _prompt_compose_profile(message: Message, draft: ProfileDraft, is_executor: bool) -> None:
    step = draft.next_field_for_compose(is_executor)
    prompts = {
        "status": ("profile.ask_status", status_keyboard()),
        "full_name": ("profile.ask_full_name", with_cancel([])),
        "passport": ("profile.ask_passport", with_cancel([])),
        "inn": ("profile.ask_inn", with_cancel([])),
        "ogrn": ("profile.ask_ogrn", with_cancel([])),
        "org_name": ("profile.ask_org_name", with_cancel([])),
        "signer_position": ("profile.ask_signer_position", with_cancel([])),
        "signer_basis": ("profile.ask_signer_basis", signer_basis_keyboard()),
        "address": ("profile.ask_address", with_cancel([])),
        "vat_mode": ("profile.ask_vat", vat_keyboard()),
        "payout": ("compose.profile.payout", with_cancel([])),
    }
    key, markup = prompts.get(step, ("profile.ask_status", status_keyboard()))
    await message.answer(t(key), reply_markup=markup)


@router.callback_query(StateFilter(ComposeStates.profile), F.data.startswith("prof:st:"))
async def compose_prof_status(cb: CallbackQuery, state: FSMContext, session) -> None:
    status = cb.data.split(":")[-1]
    draft = draft_from_dict((await state.get_data()).get("profile"))
    draft.status = status
    user = await get_or_create_user(
        session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username
    )
    await state.update_data(profile=draft.__dict__)
    await save_profile(session, user.id, draft)
    is_executor = (await state.get_data()).get("is_executor", True)
    await cb.message.answer(t("compose.profile.status_hint"))
    await _prompt_compose_profile(cb.message, draft, is_executor)
    await cb.answer()


@router.callback_query(StateFilter(ComposeStates.profile), F.data.startswith("prof:vat:"))
async def compose_prof_vat(cb: CallbackQuery, state: FSMContext, session) -> None:
    draft = draft_from_dict((await state.get_data()).get("profile"))
    draft.vat_mode = cb.data.split(":")[-1]
    user = await get_or_create_user(
        session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username
    )
    await save_profile(session, user.id, draft)
    await state.update_data(profile=draft.__dict__)
    is_executor = (await state.get_data()).get("is_executor", True)
    await _prompt_compose_profile(cb.message, draft, is_executor)
    await cb.answer()


@router.callback_query(StateFilter(ComposeStates.profile), F.data.startswith("prof:basis:"))
async def compose_prof_basis(cb: CallbackQuery, state: FSMContext, session) -> None:
    draft = draft_from_dict((await state.get_data()).get("profile"))
    draft.signer_basis = cb.data.split(":", 2)[-1]
    user = await get_or_create_user(
        session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username
    )
    await save_profile(session, user.id, draft)
    await state.update_data(profile=draft.__dict__)
    is_executor = (await state.get_data()).get("is_executor", True)
    await _prompt_compose_profile(cb.message, draft, is_executor)
    await cb.answer()


@router.message(StateFilter(ComposeStates.profile), F.text)
async def compose_prof_text(message: Message, state: FSMContext, session) -> None:
    _ = get_cipher()
    data = await state.get_data()
    draft = draft_from_dict(data.get("profile"))
    is_executor = data.get("is_executor", True)
    step = draft.next_field_for_compose(is_executor)
    if step in (None, "status", "vat_mode", "signer_basis"):
        await message.answer(t("profile.use_buttons"))
        return

    text = (message.text or "").strip()
    if step == "passport" and not validate_passport(text):
        await message.answer(t("profile.errors.passport"))
        return
    if step == "inn" and not validate_inn(text):
        await message.answer(t("profile.errors.inn"))
        return
    if step == "ogrn":
        ok = validate_ogrn(text) if draft.status == OOO else validate_ogrnip(text)
        if not ok:
            await message.answer(t("profile.errors.ogrn"))
            return

    mapping = {
        "full_name": "full_name",
        "passport": "passport",
        "inn": "inn",
        "ogrn": "ogrn",
        "org_name": "org_name",
        "signer_position": "signer_position",
        "address": "address",
        "payout": "bank",
    }
    if step == "payout":
        if "@" in text or "бик" in text.lower() or "р/с" in text.lower():
            draft.bank = text
        else:
            draft.sbp = text
    else:
        setattr(draft, mapping[step], text)

    user = await get_or_create_user(
        session, tg_user_id=message.from_user.id, tg_username=message.from_user.username
    )
    await save_profile(session, user.id, draft)
    await state.update_data(profile=draft.__dict__)

    if compose_profile_ready(draft, is_executor):
        doc_id = data.get("document_id")
        doc = await find_active_draft(session, user.id, doc_id)
        await _build_card(message, state, session, user, doc, draft)
        return
    await _prompt_compose_profile(message, draft, is_executor)


async def _build_card(message: Message, state: FSMContext, session, user, doc, draft: ProfileDraft) -> None:
    if not user.phone:
        await message.answer(t("contact.prompt"), reply_markup=contact_keyboard())
        return
    deal = dict((await state.get_data()).get("deal") or doc.deal or {})
    deal["me_name"] = draft.full_name or draft.org_name or "—"
    party = party_from_draft(draft, user.phone)
    if doc.user_role == "executor":
        vat_disp = vat_text(party)
    else:
        vat_disp = "НДС по данным исполнителя"
    left = free_contracts_left(user)
    card = format_card_text(user_role=doc.user_role or "executor", deal=deal, vat_display=vat_disp, free_left=left)

    try:
        ver, pdf_path = await render_draft_pdf(session, doc, draft, user.phone)
        if ver.version_no == 1:
            await bump_free_contract_usage(session, user)
    except Exception:
        logger.exception("draft pdf failed")
        await message.answer(t("compose.pdf_error"))
        return

    await state.set_state(ComposeStates.card)
    await state.update_data(deal=deal, document_id=doc.id)
    await message.answer(card, reply_markup=card_keyboard())
    await message.answer_document(FSInputFile(pdf_path, filename="contract_draft.pdf"))


@router.callback_query(StateFilter(ComposeStates.card), F.data == "compose:card:sign")
async def card_sign(cb: CallbackQuery) -> None:
    await cb.message.answer(t("bot.soon"), reply_markup=card_keyboard())
    await cb.answer()


@router.callback_query(F.data == "compose:card:edit")
@router.callback_query(StateFilter(ComposeStates.card), F.data == "compose:card:edit")
async def card_edit(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ComposeStates.edit_pick)
    await cb.message.answer(t("compose.edit.pick"), reply_markup=edit_fields_keyboard())
    await cb.answer()


@router.callback_query(StateFilter(ComposeStates.edit_pick), F.data.startswith("compose:edit:"))
async def edit_pick(cb: CallbackQuery, state: FSMContext, session) -> None:
    field = cb.data.split(":")[-1]
    if field == "profile":
        data = await state.get_data()
        user = await get_or_create_user(
            session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username
        )
        doc = await find_active_draft(session, user.id, data.get("document_id"))
        draft = await load_draft_from_db(session, user.id)
        is_executor = (doc.user_role if doc else "executor") == "executor"
        await state.set_state(ComposeStates.profile)
        await state.update_data(profile=draft.__dict__, is_executor=is_executor)
        await _prompt_compose_profile(cb.message, draft, is_executor)
        await cb.answer()
        return
    await state.set_state(ComposeStates.edit_value)
    await state.update_data(edit_field=field)
    if field == "payment":
        await cb.message.answer(deal_field_prompt("payment"), reply_markup=payment_keyboard())
    else:
        await cb.message.answer(deal_field_prompt(field), reply_markup=with_cancel([]))
    await cb.answer()


@router.message(StateFilter(ComposeStates.edit_value), F.text)
async def edit_value_text(message: Message, state: FSMContext, session) -> None:
    field = (await state.get_data()).get("edit_field")
    deal = dict((await state.get_data()).get("deal") or {})
    text = (message.text or "").strip()
    if field == "services":
        deal["services"] = text
    elif field == "term":
        deal["term"] = normalize_term(text)
    elif field == "price":
        p = parse_price(text)
        if p is None:
            await message.answer(deal_field_prompt("price"))
            return
        deal["price"] = p
    await _finish_edit(message, state, session, deal)


@router.callback_query(StateFilter(ComposeStates.edit_value), F.data.startswith("compose:pay:"))
async def edit_payment(cb: CallbackQuery, state: FSMContext, session) -> None:
    deal = dict((await state.get_data()).get("deal") or {})
    deal["payment"] = cb.data.split(":")[-1]
    await _finish_edit(cb.message, state, session, deal, cb=cb)


async def _finish_edit(message: Message, state: FSMContext, session, deal: dict, cb: CallbackQuery | None = None) -> None:
    user = await get_or_create_user(
        session,
        tg_user_id=(cb.from_user.id if cb else message.from_user.id),
        tg_username=(cb.from_user.username if cb else message.from_user.username),
    )
    data = await state.get_data()
    doc = await find_active_draft(session, user.id, data.get("document_id"))
    if doc:
        await save_composing_state(session, doc, role=doc.user_role, deal=deal)
    draft = await load_draft_from_db(session, user.id)
    await state.update_data(deal=deal)
    await _build_card(message, state, session, user, doc, draft)
    if cb:
        await cb.answer()


@router.callback_query(F.data == "compose:card:delete")
async def delete_ask(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ComposeStates.delete_confirm)
    await cb.message.answer(t("compose.delete.confirm"), reply_markup=delete_confirm_keyboard())
    await cb.answer()


@router.callback_query(StateFilter(ComposeStates.delete_confirm), F.data == "compose:delete:yes")
async def delete_yes(cb: CallbackQuery, state: FSMContext, session) -> None:
    data = await state.get_data()
    user = await get_or_create_user(
        session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username
    )
    doc = await find_active_draft(session, user.id, data.get("document_id"))
    if doc:
        await soft_delete_document(session, doc)
    await state.clear()
    await send_main_menu(cb.message)
    await cb.answer()


@router.callback_query(StateFilter(ComposeStates.delete_confirm), F.data == "compose:delete:no")
async def delete_no(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ComposeStates.card)
    await cb.message.answer(t("compose.delete.kept"), reply_markup=card_keyboard())
    await cb.answer()


@router.callback_query(F.data == "compose:cancel")
async def compose_cancel(cb: CallbackQuery, state: FSMContext, session) -> None:
    data = await state.get_data()
    user = await get_or_create_user(
        session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username
    )
    if data.get("document_id"):
        doc = await find_active_draft(session, user.id, data["document_id"])
        if doc:
            deal = data.get("deal") or doc.deal
            await save_composing_state(session, doc, role=doc.user_role or data.get("user_role"), deal=deal)
    await state.clear()
    await send_main_menu(cb.message)
    await cb.answer(t("compose.cancelled_toast"), show_alert=False)

