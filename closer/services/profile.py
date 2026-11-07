from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from closer.config import get_settings
from closer.db.models import Profile
from closer.documents.parties import IP, OOO
from closer.services.crypto import FieldCipher
from closer.services.profile_fields import PROFILE_FIELDS, ProfileDraft
from closer.services.validation import format_passport


def get_cipher() -> FieldCipher:
    settings = get_settings()
    if not settings.pd_encryption_key:
        raise RuntimeError("PD_ENCRYPTION_KEY is not set")
    return FieldCipher(settings.pd_encryption_key)


def profile_is_complete(draft: ProfileDraft) -> bool:
    if draft.next_field() not in (None, "email_optional", "payout_optional"):
        return False
    if draft.email is None or (draft.bank is None and draft.sbp is None):
        return False
    return True


def draft_missing_for_status(draft: ProfileDraft) -> list[str]:
    if not draft.status:
        return ["status"]
    missing = []
    for key in PROFILE_FIELDS[draft.status]:
        if not getattr(draft, key):
            missing.append(key)
    return missing


async def load_draft_from_db(session: AsyncSession, user_id: int) -> ProfileDraft:
    profile = await session.scalar(select(Profile).where(Profile.user_id == user_id))
    draft = ProfileDraft()
    if not profile:
        return draft
    draft.status = profile.status
    draft.full_name = profile.full_name
    draft.inn = profile.inn
    draft.ogrn = profile.ogrn
    draft.org_name = profile.org_name
    draft.signer_position = profile.signer_position
    draft.signer_basis = profile.signer_basis
    draft.email = profile.email or ""
    draft.bank = profile.bank or ""
    draft.sbp = profile.sbp or ""
    draft.vat_mode = profile.vat_mode
    if profile.passport_enc:
        draft.passport = get_cipher().decrypt(profile.passport_enc)
    if profile.address_enc:
        draft.address = get_cipher().decrypt(profile.address_enc)
    return draft


async def save_profile(session: AsyncSession, user_id: int, draft: ProfileDraft) -> Profile:
    cipher = get_cipher()
    profile = await session.scalar(select(Profile).where(Profile.user_id == user_id))
    if not profile:
        profile = Profile(user_id=user_id)
        session.add(profile)

    profile.status = draft.status
    profile.full_name = draft.full_name
    profile.inn = draft.inn
    profile.ogrn = draft.ogrn
    profile.org_name = draft.org_name
    profile.signer_position = draft.signer_position
    profile.signer_basis = draft.signer_basis
    profile.email = draft.email or None
    profile.bank = draft.bank or None
    profile.sbp = draft.sbp or None
    profile.vat_mode = draft.vat_mode
    if draft.status in (IP, OOO) and draft.vat_mode == "none":
        profile.vat_mode = "none"

    if draft.passport:
        profile.passport_enc = cipher.encrypt(format_passport(draft.passport))
    if draft.address:
        profile.address_enc = cipher.encrypt(draft.address)

    profile.is_complete = profile_is_complete(draft)
    await session.flush()
    return profile
