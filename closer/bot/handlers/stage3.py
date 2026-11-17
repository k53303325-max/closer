"""Stage 3: invite, counterparty, SMS signing, my contracts, verify."""

from __future__ import annotations

import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from closer.bot.compose_keyboards import with_cancel
from closer.bot.handlers.stage1_common import send_main_menu
from closer.bot.handlers.onboarding import send_pep_prompt
from closer.bot.invite_review import deliver_invite_review
from closer.bot.keyboards import contact_keyboard
from closer.bot.keyboards_stage1 import back_home_keyboard
from closer.bot.stage3_keyboards import (
    change_decision_keyboard,
    change_fields_keyboard,
    invite_preview_keyboard,
    review_keyboard,
    send_invite_card_keyboard,
    sign_confirm_keyboard,
    verify_prompt_keyboard,
)
from closer.bot.states import ChangeStates, InviteStates, OnboardingStates, SignStates
from closer.config import get_settings
from closer.db.models import Document, DocumentVersion, Signature, User
from closer.documents.docx_fill import sha256
from closer.documents.signing_sheet import build_signing_sheet_pdf
from closer.integrations.storage import get_storage
from closer.services.audit import append_audit
from closer.services.contract_build import counterparty_role
from closer.services.contracts_list import STATUS_LABELS, list_user_documents
from closer.services.documents_service import (
    bump_free_contract_usage,
    find_owner_sendable_draft,
    free_contracts_left,
    render_final_contract,
    save_composing_state,
)
from closer.services.fields_schema import payment_contract_text
from closer.services.invites import bind_counterparty, create_invite, find_doc_by_invite, invite_link, parse_start_payload
from closer.services.normalize import format_price_rub, normalize_term, parse_price
from closer.services.profile import load_draft_from_db
from closer.services.sign_flow import MAX_ATTEMPTS, issue_code, mark_signed, verify_code
from closer.services.users import get_or_create_user, user_has_pep_consent
from closer.texts import t
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = Router()

CHANGE_FIELDS = ("services", "term", "price", "payment")


def _parse_doc_id_from_send_callback(data: str, state_data: dict) -> int | None:
    parts = data.split(":")
    if len(parts) >= 4 and parts[-1].isdigit():
        return int(parts[-1])
    raw = state_data.get("document_id")
    return int(raw) if raw is not None else None


async def send_invite_from_card(
    cb: CallbackQuery,
    state: FSMContext,
    session,
    bot: Bot,
    *,
    doc_id: int | None = None,
) -> None:
    data = await state.get_data()
    if doc_id is None:
        doc_id = _parse_doc_id_from_send_callback(cb.data or "", data)
    user = await get_or_create_user(session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username)
    doc = await find_owner_sendable_draft(session, user.id, doc_id)
    if not doc or doc.status not in ("draft", "composing"):
        await cb.answer(t("stage3.send.not_ready"), show_alert=True)
        return
    if free_contracts_left(user) <= 0:
        await cb.answer(t("billing.soon", price=get_settings().contract_price_rub), show_alert=True)
        return
    token, _ = await create_invite(session, doc, user.id)
    await bump_free_contract_usage(session, user)
    me = await bot.get_me()
    link = invite_link(me.username or "", token)
    deal = doc.deal or {}
    prof = await load_draft_from_db(session, user.id)
    name = prof.full_name or cb.from_user.full_name or "—"
    price = format_price_rub(int(deal["price"])) if deal.get("price") else "—"
    share = t("stage3.send.share_text", name=name, services=deal.get("services", "—"), price=price, link=link)
    await cb.message.answer(t("stage3.send.done", link=link))
    await cb.message.answer(share)
    await state.update_data(flow="compose", document_id=doc.id, deal=deal)
    try:
        await cb.message.edit_reply_markup(reply_markup=send_invite_card_keyboard())
    except Exception:
        logger.debug("could not edit card markup", exc_info=True)
    await cb.answer()


async def _doc_for_user(session, user: User, doc_id: int | None) -> Document | None:
    if not doc_id:
        return None
    doc = await session.get(Document, doc_id)
    if not doc or doc.deleted_at:
        return None
    if user.id not in (doc.owner_user_id, doc.counterparty_user_id or -1):
        return None
    return doc


async def _latest_pdf_sha(session, doc: Document) -> str:
    ver = await session.scalar(
        select(DocumentVersion).where(
            DocumentVersion.document_id == doc.id,
            DocumentVersion.version_no == doc.current_version,
        )
    )
    return (ver.pdf_sha256 or "") if ver else ""


async def handle_invite_deep_link(message: Message, state: FSMContext, session, bot: Bot, payload: str) -> bool:
    raw = parse_start_payload(payload if payload.startswith("/start") else f"/start {payload}")
    if not raw:
        raw = payload.removeprefix("c_") if payload.startswith("c_") else payload
    doc = await find_doc_by_invite(session, raw)
    if not doc:
        await message.answer(t("stage3.invite.invalid"), reply_markup=back_home_keyboard())
        return True
    user = await get_or_create_user(session, tg_user_id=message.from_user.id, tg_username=message.from_user.username)
    if user.id == doc.owner_user_id:
        await message.answer(t("stage3.invite.own_link"), reply_markup=back_home_keyboard())
        return True
    if not await bind_counterparty(session, doc, user.id, user.id):
        await message.answer(t("stage3.invite.taken"), reply_markup=back_home_keyboard())
        return True
    cp_role = counterparty_role(doc.user_role or "executor")
    await state.update_data(flow="invite", document_id=doc.id, invite_role=cp_role)
    initiator = await session.get(User, doc.owner_user_id)
    name = (await load_draft_from_db(session, doc.owner_user_id)).full_name or (initiator.tg_username if initiator else "—")
    price = format_price_rub(int(doc.deal.get("price", 0))) if doc.deal.get("price") else "—"
    await message.answer(
        t(
            "stage3.invite.preview",
            initiator=name,
            services=doc.deal.get("services", "—"),
            price=price,
            role=t(f"compose.role.{cp_role}"),
        ),
        reply_markup=invite_preview_keyboard(),
    )
    return True


@router.callback_query(F.data == "invite:view")
async def invite_view(cb: CallbackQuery, state: FSMContext, session) -> None:
    await state.set_state(InviteStates.onboarding_gate)
    user = await get_or_create_user(session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username)
    settings = get_settings()
    data = await state.get_data()
    await state.update_data(flow="invite", document_id=data.get("document_id"))
    if not await user_has_pep_consent(session, user.id, settings.pep_offer_version):
        await send_pep_prompt(cb.message, state)
        await cb.answer()
        return
    if not user.phone:
        await state.set_state(OnboardingStates.contact)
        await cb.message.answer(t("contact.prompt"), reply_markup=contact_keyboard())
        await cb.answer()
        return
    await deliver_invite_review(cb.message, state, session, user)
    await cb.answer()


@router.callback_query(F.data == "invite:decline")
async def invite_decline(cb: CallbackQuery, state: FSMContext, session) -> None:
    data = await state.get_data()
    doc = await session.get(Document, data.get("document_id"))
    if doc:
        cp_user = await get_or_create_user(session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username)
        doc.status = "declined"
        initiator = await session.get(User, doc.owner_user_id)
        if initiator and initiator.tg_user_id:
            name = (await load_draft_from_db(session, cp_user.id)).full_name or cb.from_user.full_name or "Пользователь"
            try:
                await cb.bot.send_message(initiator.tg_user_id, t("stage3.declined", name=name))
            except Exception:
                logger.exception("notify decline")
        await append_audit(
            session,
            document_id=doc.id,
            event="declined",
            actor_user_id=cp_user.id,
            payload={},
        )
    await state.clear()
    await send_main_menu(cb.message)
    await cb.answer()


@router.callback_query(F.data.startswith("compose:card:send"))
async def card_send_invite(cb: CallbackQuery, state: FSMContext, session, bot: Bot) -> None:
    await send_invite_from_card(cb, state, session, bot)


@router.callback_query(F.data.startswith("sign:begin:"))
async def sign_begin(cb: CallbackQuery, state: FSMContext, session) -> None:
    doc_id = int(cb.data.split(":")[-1])
    user = await get_or_create_user(session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username)
    doc = await _doc_for_user(session, user, doc_id)
    if not doc:
        await cb.answer(t("compose.resume_gone"), show_alert=True)
        return
    pdf_sha = await _latest_pdf_sha(session, doc)
    digest = pdf_sha[:8].upper()
    await state.set_state(SignStates.await_code)
    await state.update_data(document_id=doc.id, pdf_sha256=pdf_sha, version_no=doc.current_version)
    await cb.message.answer(
        t("stage3.sign.prompt", number=doc.contract_number or "—", hash8=digest),
        reply_markup=with_cancel([]),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("sign:send_code:"))
async def sign_send_code(cb: CallbackQuery, state: FSMContext, session) -> None:
    doc_id = int(cb.data.split(":")[-1])
    user = await get_or_create_user(session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username)
    doc = await _doc_for_user(session, user, doc_id)
    if not doc:
        await cb.answer()
        return
    role = "initiator" if user.id == doc.owner_user_id else "counterparty"
    try:
        code, _sig = await issue_code(session, doc, user, role)
    except ValueError as exc:
        key = f"stage3.sign.err.{exc.args[0]}"
        try:
            await cb.answer(t(key), show_alert=True)
        except KeyError:
            await cb.answer(t("bot.error_generic"), show_alert=True)
        return
    await state.update_data(document_id=doc.id, pdf_sha256=await _latest_pdf_sha(session, doc))
    await cb.message.answer(t("stage3.sign.test_code", code=code))
    await cb.answer()


@router.message(StateFilter(SignStates.await_code), F.text)
async def sign_enter_code(message: Message, state: FSMContext, session, bot: Bot) -> None:
    data = await state.get_data()
    user = await get_or_create_user(session, tg_user_id=message.from_user.id, tg_username=message.from_user.username)
    doc = await session.get(Document, data.get("document_id"))
    if not doc:
        await message.answer(t("compose.resume_gone"))
        return
    role = "initiator" if user.id == doc.owner_user_id else "counterparty"
    sig = await session.scalar(
        select(Signature).where(
            Signature.document_id == doc.id,
            Signature.version_no == doc.current_version,
            Signature.user_id == user.id,
        )
    )
    if not sig or not await verify_code(session, sig, (message.text or "").strip()):
        left = max(0, MAX_ATTEMPTS - (sig.otp_attempts if sig else MAX_ATTEMPTS))
        await message.answer(t("stage3.sign.bad_code", left=left))
        return
    pdf_sha = data.get("pdf_sha256") or await _latest_pdf_sha(session, doc)
    await mark_signed(session, sig, pdf_sha)
    await _after_one_signed(message, state, session, bot, doc, user, role, pdf_sha)
    await state.clear()


async def _after_one_signed(
    message: Message,
    state: FSMContext,
    session,
    bot: Bot,
    doc: Document,
    user: User,
    role: str,
    pdf_sha: str,
) -> None:
    if role == "counterparty":
        doc.status = "awaiting_initiator_sign"
        initiator = await session.get(User, doc.owner_user_id)
        if initiator and initiator.tg_user_id:
            name = (await load_draft_from_db(session, user.id)).full_name or "Вторая сторона"
            ver = await session.scalar(
                select(DocumentVersion).where(
                    DocumentVersion.document_id == doc.id,
                    DocumentVersion.version_no == doc.current_version,
                )
            )
            path = None
            if ver and ver.pdf_storage_key:
                path = await get_storage().path_for(ver.pdf_storage_key)
            text = t("stage3.counterparty_signed", name=name, number=doc.contract_number or "—")
            await bot.send_message(initiator.tg_user_id, text, reply_markup=sign_confirm_keyboard(doc.id))
            if path:
                await bot.send_document(initiator.tg_user_id, FSInputFile(path))
        await message.answer(t("stage3.sign.done_counterparty"))
        return

    cp_id = doc.counterparty_user_id
    other_sig = None
    if cp_id:
        other_sig = await session.scalar(
            select(Signature).where(
                Signature.document_id == doc.id,
                Signature.version_no == doc.current_version,
                Signature.user_id == cp_id,
                Signature.signed_at.is_not(None),
            )
        )
    if not other_sig:
        doc.status = "awaiting_counterparty_sign"
        await message.answer(t("stage3.sign.wait_other"))
        return

    doc.status = "signed"
    await append_audit(
        session,
        document_id=doc.id,
        event="finalized",
        actor_user_id=user.id,
        doc_sha256=pdf_sha,
    )
    await _deliver_signed(bot, session, doc)
    await message.answer(t("stage3.sign.done_both"))


async def _deliver_signed(bot: Bot, session, doc: Document) -> None:
    ver = await session.scalar(
        select(DocumentVersion).where(
            DocumentVersion.document_id == doc.id,
            DocumentVersion.version_no == doc.current_version,
        )
    )
    if not ver or not ver.pdf_storage_key:
        return
    path = await get_storage().path_for(ver.pdf_storage_key)
    sheet_tmp = path.parent / "signing_sheet.pdf"
    settings = get_settings()
    parties = []
    for uid, label in ((doc.owner_user_id, "Инициатор"), (doc.counterparty_user_id, "Контрагент")):
        if not uid:
            continue
        prof = await load_draft_from_db(session, uid)
        u = await session.get(User, uid)
        sig = await session.scalar(
            select(Signature).where(
                Signature.document_id == doc.id,
                Signature.user_id == uid,
                Signature.version_no == doc.current_version,
            )
        )
        parties.append((label, prof.full_name or "—", sig.signed_at if sig else None))
    build_signing_sheet_pdf(
        contract_number=doc.contract_number or "—",
        pdf_sha256=ver.pdf_sha256 or "",
        parties=parties,
        pep_version=settings.pep_offer_version,
        out_path=str(sheet_tmp),
    )
    for uid in (doc.owner_user_id, doc.counterparty_user_id):
        if not uid:
            continue
        u = await session.get(User, uid)
        if u and u.tg_user_id:
            await bot.send_message(u.tg_user_id, t("stage3.signed.files"))
            await bot.send_document(u.tg_user_id, FSInputFile(path))
            await bot.send_document(u.tg_user_id, FSInputFile(sheet_tmp))


@router.callback_query(F.data.startswith("change:pick:"))
async def change_pick(cb: CallbackQuery) -> None:
    doc_id = int(cb.data.split(":")[-1])
    await cb.message.answer(t("stage3.change.pick"), reply_markup=change_fields_keyboard(doc_id))
    await cb.answer()


@router.callback_query(F.data.startswith("change:field:"))
async def change_field(cb: CallbackQuery, state: FSMContext) -> None:
    parts = cb.data.split(":")
    doc_id, field = int(parts[2]), parts[3]
    if field not in CHANGE_FIELDS:
        await cb.answer()
        return
    await state.set_state(ChangeStates.enter_value)
    await state.update_data(change_doc_id=doc_id, change_field=field)
    await cb.message.answer(t(f"compose.edit.{field}") + "\n" + t("stage3.change.enter"))
    await cb.answer()


@router.message(StateFilter(ChangeStates.enter_value), F.text)
async def change_enter_value(message: Message, state: FSMContext, session) -> None:
    await _submit_change(message, state, session)


async def _submit_change(message: Message, state: FSMContext, session) -> None:
    data = await state.get_data()
    doc_id = data.get("change_doc_id")
    field = data.get("change_field")
    user = await get_or_create_user(session, tg_user_id=message.from_user.id, tg_username=message.from_user.username)
    doc = await _doc_for_user(session, user, doc_id)
    if not doc or field not in CHANGE_FIELDS:
        await message.answer(t("compose.resume_gone"))
        await state.clear()
        return
    text = (message.text or "").strip()
    if field == "price":
        new_val = parse_price(text)
        if new_val is None:
            await message.answer(t("stage3.change.bad_price"))
            return
    elif field == "term":
        new_val = normalize_term(text)
    else:
        new_val = text
    old = (doc.deal or {}).get(field)
    doc.change_request = {
        "field": field,
        "old": old,
        "new": new_val,
        "by": user.id,
        "comment": "",
    }
    other_id = doc.counterparty_user_id if user.id == doc.owner_user_id else doc.owner_user_id
    other = await session.get(User, other_id) if other_id else None
    if other and other.tg_user_id:
        old_disp = old if field != "payment" else payment_contract_text(str(old or ""))
        new_disp = new_val if field != "payment" else payment_contract_text(str(new_val or ""))
        await message.bot.send_message(
            other.tg_user_id,
            t("stage3.change.proposed", field=t(f"compose.edit.{field}"), old=old_disp, new=new_disp),
            reply_markup=change_decision_keyboard(doc.id),
        )
    await state.clear()
    await message.answer(t("stage3.change.sent"))


@router.callback_query(F.data.startswith("change:accept:"))
async def change_accept(cb: CallbackQuery, state: FSMContext, session, bot: Bot) -> None:
    doc_id = int(cb.data.split(":")[-1])
    user = await get_or_create_user(session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username)
    doc = await _doc_for_user(session, user, doc_id)
    cr = dict(doc.change_request or {}) if doc else {}
    if not doc or not cr:
        await cb.answer(t("compose.resume_gone"), show_alert=True)
        return
    proposer_id = cr.get("by")
    if user.id == proposer_id:
        await cb.answer(t("stage3.change.self"), show_alert=True)
        return
    field = cr.get("field")
    deal = dict(doc.deal or {})
    deal[field] = cr.get("new")
    await save_composing_state(session, doc, role=doc.user_role, deal=deal)
    doc.change_request = {}
    for sig in await session.scalars(select(Signature).where(Signature.document_id == doc.id)):
        sig.signed_at = None
        sig.pdf_sha256 = None
        sig.otp_hash = None
    initiator_d = await load_draft_from_db(session, doc.owner_user_id)
    cp = await session.get(User, doc.counterparty_user_id) if doc.counterparty_user_id else None
    counter_d = await load_draft_from_db(session, doc.counterparty_user_id) if doc.counterparty_user_id else None
    if not cp or not counter_d:
        await cb.answer(t("bot.error_generic"), show_alert=True)
        return
    if doc.user_role == "executor":
        ex_d, cu_d = initiator_d, counter_d
        ex_p, cu_p = (await session.get(User, doc.owner_user_id)).phone or "", cp.phone or ""
    else:
        cu_d, ex_d = initiator_d, counter_d
        cu_p, ex_p = (await session.get(User, doc.owner_user_id)).phone or "", cp.phone or ""
    ver, file = await render_final_contract(session, doc, cu_d, cu_p, ex_d, ex_p)
    first_signer = "counterparty" if proposer_id == doc.owner_user_id else "initiator"
    doc.status = "awaiting_counterparty_sign" if first_signer == "counterparty" else "awaiting_initiator_sign"
    notify_uid = doc.counterparty_user_id if first_signer == "counterparty" else doc.owner_user_id
    nu = await session.get(User, notify_uid) if notify_uid else None
    if nu and nu.tg_user_id:
        await bot.send_message(nu.tg_user_id, t("stage3.change.accepted"), reply_markup=review_keyboard(doc.id))
        await bot.send_document(nu.tg_user_id, FSInputFile(file.path, filename=file.filename))
    await cb.message.answer(t("stage3.change.accepted_you"))
    await cb.answer()


@router.callback_query(F.data.startswith("change:reject:"))
async def change_reject(cb: CallbackQuery, session) -> None:
    doc_id = int(cb.data.split(":")[-1])
    user = await get_or_create_user(session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username)
    doc = await _doc_for_user(session, user, doc_id)
    cr = dict(doc.change_request or {}) if doc else {}
    proposer_id = cr.get("by")
    if not doc or not cr or user.id == proposer_id:
        await cb.answer()
        return
    doc.change_request = {}
    proposer = await session.get(User, proposer_id)
    if proposer and proposer.tg_user_id:
        await cb.bot.send_message(proposer.tg_user_id, t("stage3.change.rejected", comment=""))
    await cb.message.answer(t("stage3.change.rejected_you"))
    await cb.answer()


@router.callback_query(F.data == "menu:my")
async def menu_my(cb: CallbackQuery, session) -> None:
    user = await get_or_create_user(session, tg_user_id=cb.from_user.id, tg_username=cb.from_user.username)
    docs = await list_user_documents(session, user.id)
    if not docs:
        await cb.message.answer(t("stage3.my.empty"), reply_markup=back_home_keyboard())
        await cb.answer()
        return
    lines = [t("stage3.my.header")]
    for d in docs:
        label = STATUS_LABELS.get(d.status, d.status)
        lines.append(f"• {d.contract_number or '—'} — {label}")
    await cb.message.answer("\n".join(lines), reply_markup=back_home_keyboard())
    await cb.answer()


@router.callback_query(F.data == "menu:verify")
async def menu_verify(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SignStates.verify_upload)
    await cb.message.answer(t("stage3.verify.prompt"), reply_markup=verify_prompt_keyboard())
    await cb.answer()


@router.message(StateFilter(SignStates.verify_upload), F.document)
async def verify_document(message: Message, state: FSMContext, session) -> None:
    doc_file = message.document
    if not doc_file:
        await message.answer(t("stage3.verify.bad"))
        return
    file = await message.bot.get_file(doc_file.file_id)
    tmp = Path("/tmp") / f"verify_{doc_file.file_unique_id}.pdf"
    await message.bot.download_file(file.file_path, tmp)
    digest = sha256(tmp)
    ver = await session.scalar(select(DocumentVersion).where(DocumentVersion.pdf_sha256 == digest))
    await state.clear()
    if not ver:
        await message.answer(t("stage3.verify.not_found"), reply_markup=back_home_keyboard())
        return
    doc = await session.get(Document, ver.document_id)
    if not doc:
        await message.answer(t("stage3.verify.not_found"), reply_markup=back_home_keyboard())
        return
    sigs = list(
        await session.scalars(
            select(Signature).where(Signature.document_id == doc.id, Signature.version_no == ver.version_no)
        )
    )
    party_ids = {doc.owner_user_id, doc.counterparty_user_id or -1}
    signed = [s for s in sigs if s.user_id in party_ids and s.signed_at]
    if len(signed) < 2:
        await message.answer(t("stage3.verify.partial"), reply_markup=back_home_keyboard())
        return
    await message.answer(t("stage3.verify.ok", number=doc.contract_number or "—"), reply_markup=back_home_keyboard())