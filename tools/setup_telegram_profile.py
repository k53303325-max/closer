#!/usr/bin/env python3
"""Apply BotFather texts and avatar via Telegram Bot API (run locally)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

API = "https://api.telegram.org/bot{token}/{method}"

ABOUT = (
    "Договор оказания услуг за 10 минут: опишите сделку, проверьте и подпишите кодом из СМС. "
    "Первые 3 договора бесплатно."
)
DESCRIPTION = (
    "Closer помогает заключить договор без бумаги и встреч.\n\n"
    "1. Опишите сделку одним сообщением: что, сколько, к какому сроку.\n"
    "2. Бот соберёт договор по шаблону юриста.\n"
    "3. Отправьте ссылку второй стороне.\n"
    "4. Обе стороны подписывают кодом из СМС.\n\n"
    "Потом бот напомнит о сроке и поможет подписать акт.\n\n"
    "Подходит для физлиц, самозанятых, ИП и компаний. Первые 3 договора бесплатно."
)
COMMANDS = [
    ("start", "Начать"),
    ("new", "Новый договор"),
    ("my", "Мои договоры"),
    ("profile", "Мой профиль"),
    ("verify", "Проверить подлинность PDF"),
    ("help", "Помощь"),
]


def main() -> None:
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token and (ROOT / ".env").is_file():
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("BOT_TOKEN="):
                token = line.split("=", 1)[1].strip()
    if not token:
        raise SystemExit("BOT_TOKEN required")

    with httpx.Client(timeout=60.0) as c:
        r = c.post(API.format(token=token, method="setMyShortDescription"), json={"short_description": ABOUT})
        print("short_description", r.json())
        r = c.post(API.format(token=token, method="setMyDescription"), json={"description": DESCRIPTION})
        print("description", r.json())
        cmds = [{"command": a, "description": b} for a, b in COMMANDS]
        r = c.post(API.format(token=token, method="setMyCommands"), json={"commands": cmds})
        print("commands", r.json())

        avatar = ROOT / "brand" / "avatar.png"
        if avatar.is_file():
            with avatar.open("rb") as f:
                r = c.post(
                    API.format(token=token, method="setMyProfilePhoto"),
                    files={"photo": ("avatar.png", f, "image/png")},
                )
            print("avatar", r.json())
        else:
            print("avatar skipped", avatar)

        cover = ROOT / "brand" / "cover.png"
        if cover.is_file():
            with cover.open("rb") as f:
                r = c.post(
                    API.format(token=token, method="setMyDescriptionPhoto"),
                    files={"photo": ("cover.png", f, "image/png")},
                )
            print("cover", r.json())


if __name__ == "__main__":
    main()
