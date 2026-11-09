from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from closer.integrations.gigachat import PaymentKey

_REPO = Path(__file__).resolve().parents[2]
FIELDS_PATH = _REPO / "templates" / "uslugi" / "fields.json"

PaymentLabelKey = Literal["prepay", "postpay", "split"]

PAYMENT_UI: dict[PaymentLabelKey, str] = {
    "prepay": "Полностью после подписания договора",
    "postpay": "Полностью после подписания акта",
    "split": "50 % вперёд, 50 % после акта",
}


@lru_cache
def load_fields_schema() -> dict:
    with FIELDS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def payment_contract_text(key: PaymentKey) -> str:
    schema = load_fields_schema()
    return schema["fields"]["payment"]["options"][key]


def deal_field_prompt(field: str) -> str:
    return load_fields_schema()["fields"][field]["ask"]


DEAL_FIELD_ORDER = ("services", "term", "price", "payment")
