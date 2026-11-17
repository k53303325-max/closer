from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from closer.compat import UTC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from closer.config import get_settings
from closer.db.models import Document, Signature, User
from closer.integrations.sms import get_sms_gateway
from closer.services.audit import append_audit

CODE_LEN = 6
CODE_TTL_MIN = 5
MAX_ATTEMPTS = 5
LOCK_MINUTES = 15
RESEND_SECONDS = 60
MAX_SMS_PER_HOUR = 5


def _otp_secret() -> bytes:
    key = get_settings().pd_encryption_key or "dev-otp-secret"
    return key.encode("utf-8")


def _hash_code(code: str) -> str:
    return hmac.new(_otp_secret(), code.encode(), hashlib.sha256).hexdigest()


def generate_code() -> str:
    return f"{secrets.randbelow(10**CODE_LEN):06d}"


async def get_or_create_signature(
    session: AsyncSession,
    doc: Document,
    user: User,
    role: str,
) -> Signature:
    row = await session.scalar(
        select(Signature).where(
            Signature.document_id == doc.id,
            Signature.version_no == doc.current_version,
            Signature.user_id == user.id,
        )
    )
    if row:
        return row
    row = Signature(
        document_id=doc.id,
        version_no=doc.current_version,
        user_id=user.id,
        role=role,
    )
    session.add(row)
    await session.flush()
    return row


async def issue_code(session: AsyncSession, doc: Document, user: User, role: str) -> tuple[str, Signature]:
    sig = await get_or_create_signature(session, doc, user, role)
    now = datetime.now(UTC)
    if sig.otp_locked_until and sig.otp_locked_until > now:
        raise ValueError("locked")
    if sig.last_code_sent_at and (now - sig.last_code_sent_at).total_seconds() < RESEND_SECONDS:
        raise ValueError("cooldown")
    if sig.sms_sent_count >= MAX_SMS_PER_HOUR and sig.last_code_sent_at and (now - sig.last_code_sent_at).total_seconds() < 3600:
        raise ValueError("hour_limit")

    code = generate_code()
    sig.otp_hash = _hash_code(code)
    sig.otp_expires_at = now + timedelta(minutes=CODE_TTL_MIN)
    sig.last_code_sent_at = now
    sig.sms_sent_count = (sig.sms_sent_count or 0) + 1
    await session.flush()

    gateway = get_sms_gateway()
    if user.phone:
        await gateway.send_otp(user.phone, f"Closer: код {code} для подписания договора {doc.contract_number}")
    await append_audit(
        session,
        document_id=doc.id,
        event="code_sent",
        actor_user_id=user.id,
        payload={"version_no": doc.current_version, "role": role},
    )
    return code, sig


async def verify_code(session: AsyncSession, sig: Signature, code: str) -> bool:
    now = datetime.now(UTC)
    if sig.otp_locked_until and sig.otp_locked_until > now:
        return False
    if not sig.otp_hash or not sig.otp_expires_at or sig.otp_expires_at < now:
        return False
    if not hmac.compare_digest(sig.otp_hash, _hash_code(code.strip())):
        sig.otp_attempts += 1
        if sig.otp_attempts >= MAX_ATTEMPTS:
            sig.otp_locked_until = now + timedelta(minutes=LOCK_MINUTES)
        await session.flush()
        return False
    return True


async def mark_signed(session: AsyncSession, sig: Signature, pdf_sha256: str) -> None:
    sig.signed_at = datetime.now(UTC)
    sig.pdf_sha256 = pdf_sha256
    sig.otp_hash = None
    await session.flush()
    await append_audit(
        session,
        document_id=sig.document_id,
        event="signed",
        actor_user_id=sig.user_id,
        doc_sha256=pdf_sha256,
        payload={"version_no": sig.version_no, "role": sig.role},
    )