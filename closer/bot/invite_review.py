"""Counterparty invite: PDF review after profile is ready."""

from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from sqlalchemy import select

from closer.bot.stage3_keyboards import review_keyboard
from closer.bot.states import InviteStates
from closer.db.models import Document, User
from closer.services.contract_build import counterparty_role
from closer.services.documents_service import render_final_contract
from closer.services.profile import load_draft_from_db, profile_ready_for_contract
from closer.bot.handlers.compose import _prompt_compose_profile
from closer.texts import t


async def deliver_invite_review(message: Message, state: FSMContext, session, user: User) -> None:
    data = await state.get_data()
    doc_id = data.get("document_id")
    if not doc_id:
        await message.answer(t("compose.resume_gone"))
        return
    doc = await session.scalar(select(Document).where(Document.id == doc_id))
    if not doc:
        await message.answer(t("compose.resume_gone"))
        return
    cp_role = data.get("invite_role") or counterparty_role(doc.user_role or "executor")
    is_executor = cp_role == "executor"
    draft = await load_draft_from_db(session, user.id)
    if not profile_ready_for_contract(draft, is_executor):
        await state.set_state(InviteStates.profile)
        await state.update_data(profile=draft.__dict__, is_executor=is_executor, flow="invite")
        await _prompt_compose_profile(message, draft, is_executor)
        return

    initiator_draft = await load_draft_from_db(session, doc.owner_user_id)
    initiator_user = await session.get(User, doc.owner_user_id)
    if doc.user_role == "executor":
        executor_d, customer_d = initiator_draft, draft
        executor_p, customer_p = (initiator_user.phone or "" if initiator_user else ""), user.phone or ""
    else:
        customer_d, executor_d = initiator_draft, draft
        customer_p, executor_p = (initiator_user.phone or "" if initiator_user else ""), user.phone or ""

    ver, file = await render_final_contract(session, doc, customer_d, customer_p, executor_d, executor_p)
    await state.set_state(InviteStates.review)
    await state.update_data(
        flow="invite",
        document_id=doc.id,
        pdf_sha256=ver.pdf_sha256,
        version_no=doc.current_version,
    )
    await message.answer(t("stage3.review.ready"), reply_markup=review_keyboard(doc.id))
    await message.answer_document(FSInputFile(file.path, filename=file.filename))