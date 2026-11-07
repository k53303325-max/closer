from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from closer.db.models import Consent, Profile, User


async def get_or_create_user(
    session: AsyncSession,
    *,
    tg_user_id: int,
    tg_username: str | None,
) -> User:
    user = await session.scalar(select(User).where(User.tg_user_id == tg_user_id))
    if user:
        if tg_username and user.tg_username != tg_username:
            user.tg_username = tg_username
        return user
    user = User(tg_user_id=tg_user_id, tg_username=tg_username)
    session.add(user)
    await session.flush()
    return user


async def user_has_pep_consent(session: AsyncSession, user_id: int, version: str) -> bool:
    q = select(Consent).where(
        Consent.user_id == user_id,
        Consent.kind == "pep_offer",
        Consent.doc_version == version,
    )
    return (await session.scalar(q)) is not None


async def user_has_complete_profile(session: AsyncSession, user_id: int) -> bool:
    profile = await session.scalar(select(Profile).where(Profile.user_id == user_id))
    return profile is not None and profile.is_complete


async def save_phone(session: AsyncSession, user: User, phone: str) -> None:
    user.phone = phone
    user.phone_verified_at = datetime.now(UTC)
