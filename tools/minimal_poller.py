#!/usr/bin/env python3
"""Temporary polling until Vercel has BOT_TOKEN + DB (run: python tools/minimal_poller.py)."""
from __future__ import annotations

import os
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
def load_welcome() -> str:
    path = ROOT / "texts" / "ru.yaml"
    if path.is_file():
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        w = (data.get("start") or {}).get("welcome")
        if w:
            return str(w).strip()
    return (
        "Здравствуйте! Я Closer — помогаю оформить договор оказания услуг в Telegram.\n\n"
        "Полный сценарий подключаем на сервере; если видите это — бот на связи."
    )


def load_token() -> str:
    token = os.environ.get("BOT_TOKEN", "")
    if not token:
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("BOT_TOKEN="):
                token = line.split("=", 1)[1].strip()
    if not token:
        raise SystemExit("BOT_TOKEN missing")
    return token


def main() -> None:
    token = load_token()
    base = f"https://api.telegram.org/bot{token}"
    offset = 0
    welcome = load_welcome()
    print("minimal poller running (Ctrl+C to stop)", flush=True)
    with httpx.Client(timeout=35.0) as c:
        while True:
            r = c.get(f"{base}/getUpdates", params={"offset": offset, "timeout": 25})
            r.raise_for_status()
            for item in r.json().get("result", []):
                offset = item["update_id"] + 1
                msg = item.get("message") or {}
                text = (msg.get("text") or "").strip()
                chat_id = msg.get("chat", {}).get("id")
                if not chat_id:
                    continue
                print(f"update chat={chat_id} text={text!r}", flush=True)
                if text.startswith("/start"):
                    c.post(f"{base}/sendMessage", json={"chat_id": chat_id, "text": welcome})
                elif text == "/help":
                    c.post(
                        f"{base}/sendMessage",
                        json={"chat_id": chat_id, "text": "Помощь: /start — начать. Сервер настраивается."},
                    )
            time.sleep(0.5)


if __name__ == "__main__":
    main()
