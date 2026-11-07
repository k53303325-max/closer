from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal, Protocol, TypedDict

import httpx

logger = logging.getLogger(__name__)

PaymentKey = Literal["prepay", "postpay", "split"]


class ExtractResult(TypedDict, total=False):
    supported: bool
    reason: str
    services: str | None
    term: str | None
    price: int | None
    payment: PaymentKey | None


class LLMClient(Protocol):
    async def classify_and_extract(self, user_text: str) -> ExtractResult: ...


class FakeLLM:
    """Deterministic stub until GigaChat credentials are available."""

    async def classify_and_extract(self, user_text: str) -> ExtractResult:
        text = user_text.lower()
        unsupported_hints = ("купить", "продать", "товар", "авто", "квартиру", "ремонт с материал")
        if any(h in text for h in unsupported_hints):
            return {"supported": False, "reason": "unsupported_deal_type"}

        price_match = re.search(r"(\d[\d\s]{2,})", user_text.replace("\u00a0", " "))
        price = int(re.sub(r"\s", "", price_match.group(1))) if price_match else None

        payment: PaymentKey | None = None
        if "после" in text and "акт" in text:
            payment = "postpay"
        elif "50" in text or "половин" in text or "аванс" in text:
            payment = "split"
        elif price:
            payment = "prepay"

        services = "оказанию услуг по запросу пользователя"
        if "логотип" in text:
            services = "разработке логотипа"
        elif "уборк" in text:
            services = "уборке помещения"

        return {
            "supported": True,
            "services": services,
            "term": "до 30.11.2026",
            "price": price,
            "payment": payment,
        }


class GigaChatClient:
    """GigaChat Lite via Sber API (enabled when GIGACHAT_AUTH_KEY is set)."""

    def __init__(self, auth_key: str) -> None:
        self._auth_key = auth_key

    async def classify_and_extract(self, user_text: str) -> ExtractResult:
        # Minimal wiring: OAuth + chat/completions to be filled when key is available.
        async with httpx.AsyncClient(timeout=60.0) as client:
            _ = client  # placeholder for stage 2
        logger.warning("GigaChatClient: API call not implemented yet, falling back shape")
        payload = {
            "supported": True,
            "services": None,
            "term": None,
            "price": None,
            "payment": None,
        }
        return json.loads(json.dumps(payload))


def get_llm_client(auth_key: str | None) -> LLMClient:
    if auth_key:
        return GigaChatClient(auth_key)
    return FakeLLM()
