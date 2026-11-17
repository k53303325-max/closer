from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from closer.compat import UTC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from closer.db.models import Document
from closer.services.audit import append_audit

INVITE_DAYS = 7
INVITE_PREFIX = "c_"


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def mint_invite_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(24)
    return f"{INVITE_PREFIX}{raw}", _hash_token(raw)


def parse_start_payload(text: str | None) -> str | None:
    if not text:
        return None
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return None
    payload = parts[1].strip()
    if payload.startswith(INVITE_PREFIX):
        return payload[len(INVITE_PREFIX) :]
    return None


async def create_invite(session: AsyncSession, doc: Document, actor_user_id: int) -> tuple[str, str]:
    raw, digest = mint_invite_token()
    doc.invite_token_hash = digest
    doc.invite_expires_at = datetime.now(UTC) + timedelta(days=INVITE_DAYS)
    doc.status = "awaiting_counterparty"
    await session.flush()
    await append_audit(
        session,
        document_id=doc.id,
        event="invite_created",
        actor_user_id=actor_user_id,
        payload={"expires_at": doc.invite_expires_at.isoformat()},
    )
    deep_link_token = raw
    return deep_link_token, digest


async def find_doc_by_invite(session: AsyncSession, raw_token: str) -> Document | None:
    digest = _hash_token(raw_token)
    doc = await session.scalar(select(Document).where(Document.invite_token_hash == digest))
    if not doc or doc.deleted_at:
        return None
    if doc.invite_expires_at and doc.invite_expires_at < datetime.now(UTC):
        return None
    return doc


def invite_link(bot_username: str, raw_token: str) -> str:
    payload = raw_token if raw_token.startswith(INVITE_PREFIX) else f"{INVITE_PREFIX}{raw_token}"
    return f"https://t.me/{bot_username}?start={payload}"


async def bind_counterparty(session: AsyncSession, doc: Document, user_id: int, actor_user_id: int) -> bool:
    if doc.counterparty_user_id and doc.counterparty_user_id != user_id:
        return False
    doc.counterparty_user_id = user_id
    await session.flush()
    await append_audit(
        session,
        document_id=doc.id,
        event="invite_opened",
        actor_user_id=actor_user_id,
        payload={"counterparty_user_id": user_id},
    )
    return True