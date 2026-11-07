from __future__ import annotations

from dataclasses import dataclass

from closer.documents.parties import INDIVIDUAL, IP, OOO, SELF_EMPLOYED

PROFILE_FIELDS: dict[str, list[str]] = {
    INDIVIDUAL: ["full_name", "passport"],
    SELF_EMPLOYED: ["full_name", "passport", "inn"],
    IP: ["full_name", "inn", "ogrn", "address", "vat_mode"],
    OOO: ["org_name", "full_name", "signer_position", "signer_basis", "inn", "ogrn", "address", "vat_mode"],
}


@dataclass
class ProfileDraft:
    status: str | None = None
    full_name: str | None = None
    passport: str | None = None
    inn: str | None = None
    ogrn: str | None = None
    org_name: str | None = None
    signer_position: str | None = None
    signer_basis: str | None = None
    address: str | None = None
    email: str | None = None
    bank: str | None = None
    sbp: str | None = None
    vat_mode: str = "none"

    def next_field(self) -> str | None:
        if not self.status:
            return "status"
        for key in PROFILE_FIELDS[self.status]:
            if getattr(self, key) in (None, ""):
                return key
        if self.email is None:
            return "email_optional"
        if self.bank is None and self.sbp is None:
            return "payout_optional"
        return None


def draft_from_dict(raw: dict | None) -> ProfileDraft:
    raw = raw or {}
    allowed = {f.name for f in ProfileDraft.__dataclass_fields__.values()}
    return ProfileDraft(**{k: raw[k] for k in allowed if k in raw})
