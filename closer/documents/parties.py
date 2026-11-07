"""Text of the «Стороны» line, the requisites block and the VAT phrase, built from a party profile.

One contract template serves every combination of parties; only these three strings
depend on the party's status. Field names match docs/spec.md, section «Профиль».
"""
from __future__ import annotations

from dataclasses import dataclass

INDIVIDUAL, SELF_EMPLOYED, IP, OOO = "individual", "self_employed", "ip", "ooo"

# vat_mode is asked once in the profile of an IP / OOO
VAT_TEXT = {
    "none": "НДС не облагается",
    "vat22": "включая НДС 22 %",
    "vat7": "включая НДС 7 %",
    "vat5": "включая НДС 5 %",
}


@dataclass
class Party:
    status: str                       # individual | self_employed | ip | ooo
    full_name: str                    # ФИО (для ООО — ФИО подписанта)
    phone: str
    passport: str | None = None       # «1234 567890» — физлицо и самозанятый
    inn: str | None = None            # самозанятый, ИП, ООО
    ogrn: str | None = None           # ОГРНИП / ОГРН
    org_name: str | None = None       # ООО: «ООО «Ромашка»»
    signer_position: str | None = None  # ООО: «генерального директора» (родительный падеж)
    signer_basis: str | None = None   # ООО: «Устава» / «доверенности № 5 от 01.10.2026»
    address: str | None = None        # ИП, ООО — адрес из ЕГРИП/ЕГРЮЛ
    email: str | None = None
    bank: str | None = None           # «АО «Т-Банк», БИК 044525974, к/с …, р/с …»
    sbp: str | None = None            # «+7 900 000-00-00, Т-Банк»
    vat_mode: str = "none"            # для ИП/ООО; у физлица и самозанятого всегда none


def party_line(p: Party) -> str:
    if p.status == INDIVIDUAL:
        return f"{p.full_name}, паспорт {p.passport}"
    if p.status == SELF_EMPLOYED:
        return f"{p.full_name}, паспорт {p.passport}, ИНН {p.inn}, плательщик налога на профессиональный доход"
    if p.status == IP:
        return f"Индивидуальный предприниматель {p.full_name}, ОГРНИП {p.ogrn}, ИНН {p.inn}"
    if p.status == OOO:
        return (f"{p.org_name}, ИНН {p.inn}, ОГРН {p.ogrn}, в лице {p.signer_position} "
                f"{p.full_name}, действующего на основании {p.signer_basis}")
    raise ValueError(f"unknown status {p.status}")


def party_details(p: Party) -> str:
    """Multi-line requisites block; lines are joined with \\n (rendered as line breaks)."""
    lines: list[str] = []
    if p.status == OOO:
        lines += [p.org_name, f"ИНН {p.inn}, ОГРН {p.ogrn}", f"Адрес: {p.address}"]
    elif p.status == IP:
        lines += [f"ИП {p.full_name}", f"ИНН {p.inn}, ОГРНИП {p.ogrn}", f"Адрес: {p.address}"]
    else:
        lines += [p.full_name, f"Паспорт: {p.passport}"]
        if p.inn:
            lines.append(f"ИНН {p.inn}")
    lines.append(f"Телефон: {p.phone}")
    if p.email:
        lines.append(f"Email: {p.email}")
    if p.bank:
        lines.append(f"Банк: {p.bank}")
    if p.sbp:
        lines.append(f"СБП: {p.sbp}")
    return "\n".join(x for x in lines if x)


def vat_text(executor: Party) -> str:
    if executor.status in (INDIVIDUAL, SELF_EMPLOYED):
        return VAT_TEXT["none"]
    return VAT_TEXT[executor.vat_mode]


def sign_name(p: Party) -> str:
    """Name under the signature line: «И. И. Иванов»-style is not required — full name is fine."""
    return p.full_name
