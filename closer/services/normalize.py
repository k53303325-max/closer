from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

_MOSCOW = ZoneInfo("Europe/Moscow")

MONTHS_RU = {
    "январ": 1,
    "феврал": 2,
    "март": 3,
    "апрел": 4,
    "ма": 5,
    "июн": 6,
    "июл": 7,
    "август": 8,
    "сентябр": 9,
    "октябр": 10,
    "ноябр": 11,
    "декабр": 12,
}


def today_moscow() -> date:
    return datetime.now(_MOSCOW).date()


def format_contract_date(d: date | None = None) -> str:
    d = d or today_moscow()
    return d.strftime("%d.%m.%Y")


def format_price_rub(amount: int) -> str:
    s = f"{amount:,}".replace(",", " ")
    return s


def parse_price(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text.replace("\u00a0", " "))
    if not digits:
        return None
    return int(digits)


def normalize_term(raw: str, base: date | None = None) -> str:
    base = base or today_moscow()
    text = raw.strip().lower().replace("ё", "е")

    m = re.search(r"(\d+)\s*(недел|месяц|дн)", text)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if unit.startswith("недел"):
            end = base + timedelta(weeks=n)
        elif unit.startswith("месяц"):
            end = base + timedelta(days=30 * n)
        else:
            end = base + timedelta(days=n)
        return f"до {end.strftime('%d.%m.%Y')}"

    iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if iso:
        d = date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        return f"до {d.strftime('%d.%m.%Y')}"

    dotted = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})", raw)
    if dotted:
        day, month, year = int(dotted.group(1)), int(dotted.group(2)), int(dotted.group(3))
        if year < 100:
            year += 2000
        d = date(year, month, day)
        if "с " in text and " по " in text:
            parts = re.findall(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})", raw)
            if len(parts) >= 2:
                d1 = date(int(parts[0][2]) if int(parts[0][2]) > 99 else int(parts[0][2]) + 2000,
                          int(parts[0][1]), int(parts[0][0]))
                d2 = date(int(parts[1][2]) if int(parts[1][2]) > 99 else int(parts[1][2]) + 2000,
                          int(parts[1][1]), int(parts[1][0]))
                return f"с {d1.strftime('%d.%m.%Y')} по {d2.strftime('%d.%m.%Y')}"
        if text.startswith("до") or "до " in text:
            return f"до {d.strftime('%d.%m.%Y')}"
        return f"до {d.strftime('%d.%m.%Y')}"

    for stem, month in MONTHS_RU.items():
        if stem in text:
            year_m = re.search(r"(20\d{2})", raw)
            year = int(year_m.group(1)) if year_m else base.year
            day_m = re.search(r"(\d{1,2})\s+" + stem[:4], text)
            day = int(day_m.group(1)) if day_m else 1
            d = date(year, month, min(day, 28))
            return f"до {d.strftime('%d.%m.%Y')}"

    if text.startswith("до"):
        return raw.strip()
    return raw.strip()
