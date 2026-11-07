from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from closer.db.models import AuditLog


def _canon(obj: dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


async def append_audit(
    session: AsyncSession,
    *,
    event: str,
    actor_user_id: int | None,
    document_id: int | None = None,
    payload: dict[str, Any] | None = None,
    doc_sha256: str | None = None,
    pep_version: str | None = None,
) -> AuditLog:
    payload = dict(payload or {})
    if pep_version:
        payload.setdefault("pep_version", pep_version)

    last = await session.scalar(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
    prev_hash = last.record_hash if last else "0" * 64

    record = {
        "ts": datetime.now(UTC).isoformat(),
        "event": event,
        "actor_user_id": actor_user_id,
        "document_id": document_id,
        "payload": payload,
        "doc_sha256": doc_sha256,
        "prev_hash": prev_hash,
    }
    record_hash = hashlib.sha256(_canon(record).encode("utf-8")).hexdigest()

    row = AuditLog(
        document_id=document_id,
        event=event,
        actor_user_id=actor_user_id,
        payload=payload,
        doc_sha256=doc_sha256,
        prev_hash=prev_hash,
        record_hash=record_hash,
    )
    session.add(row)
    await session.flush()
    return row
