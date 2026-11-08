"""Vercel serverless: Telegram webhook."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if "setup=1" in (self.path or ""):
            secret = os.environ.get("SETUP_SECRET", "")
            query_secret = ""
            if "secret=" in (self.path or ""):
                query_secret = self.path.split("secret=", 1)[-1].split("&", 1)[0]
            if secret and query_secret != secret:
                self._json(403, {"ok": False, "error": "forbidden"})
                return
            base = os.environ.get("WEBHOOK_URL", "").strip()
            if not base:
                self._json(400, {"ok": False, "error": "WEBHOOK_URL missing"})
                return
            try:
                from closer.bot.runtime import set_webhook

                webhook = asyncio.run(set_webhook(base))
                self._json(200, {"ok": True, "webhook": webhook})
            except Exception as exc:
                logger.exception("webhook setup")
                self._json(500, {"ok": False, "error": str(exc)})
            return
        self._json(200, {"ok": True, "service": "closer-telegram-webhook"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "error": "invalid json"})
            return
        try:
            from closer.bot.runtime import process_update

            asyncio.run(process_update(data))
            self._json(200, {"ok": True})
        except Exception:
            logger.exception("update failed")
            if _try_emergency_start_reply(data):
                self._json(200, {"ok": True, "fallback": True})
            else:
                self._json(500, {"ok": False})


def _try_emergency_start_reply(data: dict) -> bool:
    """If full stack is down (no env/DB), at least answer /start via Bot API."""
    try:
        import httpx
        import yaml

        msg = data.get("message") or {}
        text = (msg.get("text") or "").strip()
        if not text.startswith("/start"):
            return False
        token = os.environ.get("BOT_TOKEN", "").strip()
        chat_id = msg.get("chat", {}).get("id")
        if not token or not chat_id:
            return False
        texts_path = _ROOT / "texts" / "ru.yaml"
        welcome = "Здравствуйте! Я Closer — договор оказания услуг в Telegram."
        if texts_path.is_file():
            raw = yaml.safe_load(texts_path.read_text(encoding="utf-8"))
            welcome = (raw.get("start") or {}).get("welcome", welcome).strip()
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": welcome},
            timeout=15.0,
        ).raise_for_status()
        return True
    except Exception:
        logger.exception("emergency /start reply failed")
        return False

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        logger.info("%s - %s", self.address_string(), format % args)

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
