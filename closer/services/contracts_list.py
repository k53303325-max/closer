from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from closer.db.models import Document

STATUS_LABELS = {
    "composing": "Черновик (заполняется)",
    "draft": "Черновик",
    "awaiting_counterparty": "Ждёт вторую сторону",
    "awaiting_initiator_sign": "Ждёт вашу подпись",
    "awaiting_counterparty_sign": "Ждёт подпись второй стороны",
    "signed": "Подписан",
    "declined": "Отклонён",
    "deleted": "Удалён",
}


async def list_user_documents(session: AsyncSession, user_id: int) -> list[Document]:
    return list(
        await session.scalars(
            select(Document)
            .where(
                Document.deleted_at.is_(None),
                or_(Document.owner_user_id == user_id, Document.counterparty_user_id == user_id),
                Document.status != "deleted",
            )
            .order_by(Document.updated_at.desc())
            .limit(30)
        )
    )