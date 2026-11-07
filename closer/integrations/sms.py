from __future__ import annotations

import logging
import uuid
from typing import Protocol
from urllib.parse import urlencode

import httpx

from closer.config import Settings, get_settings

logger = logging.getLogger(__name__)


class SmsGateway(Protocol):
    async def send_otp(self, phone: str, message: str) -> str:
        """Send SMS; return provider message id."""


def _normalize_phone(phone: str) -> str:
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    return digits


class FakeSmsGateway:
    def __init__(self, test_phone: str | None = None) -> None:
        self._test_phone = test_phone

    async def send_otp(self, phone: str, message: str) -> str:
        target = self._test_phone or phone
        msg_id = f"fake-{uuid.uuid4().hex[:12]}"
        logger.info("FakeSms to %s: %s (id=%s)", _mask_phone(target), message, msg_id)
        return msg_id


class SmscGateway:
    """https://smsc.ru/"""

    def __init__(self, login: str, password: str) -> None:
        self._login = login
        self._password = password

    async def send_otp(self, phone: str, message: str) -> str:
        params = {
            "login": self._login,
            "psw": self._password,
            "phones": _normalize_phone(phone),
            "mes": message,
            "fmt": 3,
        }
        url = f"https://smsc.ru/sys/send.php?{urlencode(params)}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
        if "error" in data:
            raise RuntimeError(f"SMSC error: {data.get('error')}")
        return str(data.get("id", data))


class SmsAeroGateway:
    """https://smsaero.ru/"""

    def __init__(self, email: str, api_key: str) -> None:
        self._email = email
        self._api_key = api_key

    async def send_otp(self, phone: str, message: str) -> str:
        url = "https://gate.smsaero.ru/v2/sms/send"
        payload = {
            "number": _normalize_phone(phone),
            "text": message,
            "sign": "Closer",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                url,
                json=payload,
                auth=(self._email, self._api_key),
            )
            r.raise_for_status()
            data = r.json()
        if not data.get("success"):
            raise RuntimeError(f"SMS Aero error: {data}")
        return str(data.get("data", {}).get("id", uuid.uuid4().hex))


def _mask_phone(phone: str) -> str:
    d = _normalize_phone(phone)
    if len(d) < 4:
        return "***"
    return f"+{d[0]} *** ***-**-{d[-2:]}"


def get_sms_gateway(settings: Settings | None = None) -> SmsGateway:
    settings = settings or get_settings()
    provider = (settings.sms_provider or "fake").lower()
    if provider == "fake":
        return FakeSmsGateway(settings.sms_test_phone)
    if provider == "smsc":
        login = settings.sms_login or ""
        password = settings.sms_api_key or ""
        if not login or not password:
            raise RuntimeError("SMSC requires SMS_LOGIN and SMS_API_KEY")
        return SmscGateway(login, password)
    if provider in ("smsaero", "sms_aero", "aero"):
        email = settings.sms_login or ""
        api_key = settings.sms_api_key or ""
        if not email or not api_key:
            raise RuntimeError("SMS Aero requires SMS_LOGIN (email) and SMS_API_KEY")
        return SmsAeroGateway(email, api_key)
    raise ValueError(f"Unknown SMS_PROVIDER: {settings.sms_provider}")
