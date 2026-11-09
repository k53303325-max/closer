from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from closer.db.models import Document
from closer.documents.parties import INDIVIDUAL, Party, party_details, party_line, sign_name, vat_text
from closer.services.fields_schema import payment_contract_text
from closer.services.normalize import format_contract_date, format_price_rub
from closer.services.profile_fields import ProfileDraft
from closer.texts import t

OTHER_PARTY_LINE = "заполнит вторая сторона"
OTHER_PARTY_DETAILS = "будет заполнено второй стороной"
OTHER_PARTY_SIGN = " "


def party_from_draft(draft: ProfileDraft, phone: str) -> Party:
    return Party(
        status=draft.status or INDIVIDUAL,
        full_name=draft.full_name or "",
        phone=phone,
        passport=draft.passport,
        inn=draft.inn,
        ogrn=draft.ogrn,
        org_name=draft.org_name,
        signer_position=draft.signer_position,
        signer_basis=draft.signer_basis,
        address=draft.address,
        email=draft.email or None,
        bank=draft.bank or None,
        sbp=draft.sbp or None,
        vat_mode=draft.vat_mode,
    )


async def next_contract_number(session: AsyncSession, year: int | None = None) -> str:
    year = year or datetime.now(UTC).year
    prefix = f"CL-{year}-"
    q = await session.execute(
        select(func.count()).select_from(Document).where(Document.contract_number.like(f"{prefix}%"))
    )
    n = (q.scalar() or 0) + 1
    return f"{prefix}{n:06d}"


def build_contract_values(
    *,
    contract_number: str,
    user_party: Party,
    user_role: str,
    deal: dict,
) -> dict[str, str]:
    payment_key = deal.get("payment")
    payment = payment_contract_text(payment_key) if payment_key else ""

    if user_role == "executor":
        executor = user_party
        customer_line = OTHER_PARTY_LINE
        customer_details = OTHER_PARTY_DETAILS
        customer_sign = OTHER_PARTY_SIGN
        executor_line = party_line(executor)
        executor_details = party_details(executor)
        executor_sign = sign_name(executor)
        vat = vat_text(executor)
    else:
        customer = user_party
        customer_line = party_line(customer)
        customer_details = party_details(customer)
        customer_sign = sign_name(customer)
        executor_line = OTHER_PARTY_LINE
        executor_details = OTHER_PARTY_DETAILS
        executor_sign = OTHER_PARTY_SIGN
        vat = "НДС не облагается"

    return {
        "number": contract_number,
        "date": format_contract_date(),
        "customer": customer_line,
        "executor": executor_line,
        "services": deal.get("services") or "",
        "term": deal.get("term") or "",
        "price": format_price_rub(int(deal["price"])) if deal.get("price") else "",
        "vat": vat,
        "payment": payment,
        "customer_details": customer_details,
        "executor_details": executor_details,
        "customer_sign": customer_sign,
        "executor_sign": executor_sign,
    }


def format_card_text(
    *,
    user_role: str,
    deal: dict,
    vat_display: str,
    free_left: int,
) -> str:
    role_customer = t("compose.card.customer")
    role_executor = t("compose.card.executor")
    if user_role == "executor":
        me_line = f"{role_executor}: {deal.get('me_name', '—')}"
        other_line = f"{role_customer}: {t('compose.card.other_party')}"
    else:
        me_line = f"{role_customer}: {deal.get('me_name', '—')}"
        other_line = f"{role_executor}: {t('compose.card.other_party')}"
    payment_key = deal.get("payment")
    pay = payment_contract_text(payment_key) if payment_key else "—"
    price = format_price_rub(int(deal["price"])) if deal.get("price") else "—"
    return t(
        "compose.card.body",
        me=me_line,
        other=other_line,
        services=deal.get("services") or "—",
        term=deal.get("term") or "—",
        price=price,
        vat=vat_display,
        payment=pay,
        free_left=free_left,
    )
