from __future__ import annotations

import tempfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from closer.config import get_settings
from closer.db.models import Document, DocumentVersion, User
from closer.documents.docx_fill import fill_docx, sha256, to_pdf
from closer.integrations.storage import get_storage
from closer.services.contract_build import build_contract_values, next_contract_number, party_from_draft
from closer.services.draft_watermark import apply_draft_watermark
from closer.services.profile_fields import ProfileDraft

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates" / "uslugi"

FREE_CONTRACTS = 3


def free_contracts_left(user: User) -> int:
    return max(0, FREE_CONTRACTS - user.free_contracts_used)


async def find_incomplete_document(session: AsyncSession, user_id: int) -> Document | None:
    return await session.scalar(
        select(Document)
        .where(
            Document.owner_user_id == user_id,
            Document.status.in_(("composing", "draft")),
            Document.deleted_at.is_(None),
        )
        .order_by(Document.updated_at.desc())
        .limit(1)
    )


async def find_active_draft(session: AsyncSession, user_id: int, doc_id: int) -> Document | None:
    return await session.scalar(
        select(Document).where(
            Document.id == doc_id,
            Document.owner_user_id == user_id,
            Document.status.in_(("composing", "draft")),
            Document.deleted_at.is_(None),
        )
    )


async def create_composing_document(
    session: AsyncSession,
    user_id: int,
    user_role: str | None = None,
) -> Document:
    doc = Document(owner_user_id=user_id, user_role=user_role, status="composing", deal={})
    session.add(doc)
    await session.flush()
    return doc


async def save_composing_state(session: AsyncSession, doc: Document, *, role: str | None, deal: dict) -> None:
    if role:
        doc.user_role = role
    doc.deal = deal
    await session.flush()


async def soft_delete_document(session: AsyncSession, doc: Document) -> None:
    from datetime import UTC, datetime

    doc.status = "deleted"
    doc.deleted_at = datetime.now(UTC)


async def render_draft_pdf(
    session: AsyncSession,
    doc: Document,
    draft: ProfileDraft,
    phone: str,
) -> tuple[DocumentVersion, Path]:
    if not doc.contract_number:
        doc.contract_number = await next_contract_number(session)
    user_party = party_from_draft(draft, phone)
    values = build_contract_values(
        contract_number=doc.contract_number,
        user_party=user_party,
        user_role=doc.user_role or "executor",
        deal=doc.deal,
    )
    doc.status = "draft"
    version_no = doc.current_version + 1
    doc.current_version = version_no

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        docx_path = tmp_path / "contract.docx"
        fill_docx(TEMPLATE_DIR / "contract.docx", values, docx_path)
        raw_pdf = to_pdf(docx_path, tmp_path)
        wm_pdf = tmp_path / "contract_wm.pdf"
        apply_draft_watermark(raw_pdf, wm_pdf)

        storage = get_storage()
        key = f"drafts/{doc.owner_user_id}/{doc.id}/v{version_no}.pdf"
        await storage.put_file(key, wm_pdf)
        digest = sha256(wm_pdf)

    ver = DocumentVersion(
        document_id=doc.id,
        version_no=version_no,
        values=values,
        pdf_storage_key=key,
        pdf_sha256=digest,
    )
    session.add(ver)
    await session.flush()
    local_path = Path(await storage.path_for(key))
    return ver, local_path


async def bump_free_contract_usage(session: AsyncSession, user: User) -> None:
    if user.free_contracts_used < FREE_CONTRACTS:
        user.free_contracts_used += 1
        await session.flush()
