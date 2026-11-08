#!/usr/bin/env python3
"""Этап 1: выставить описание и команды бота из texts/ru.yaml (запуск локально)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.telegram.org/bot{token}/{method}"


def load_texts() -> dict:
    with (ROOT / "texts" / "ru.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_token() -> str:
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token and (ROOT / ".env").is_file():
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("BOT_TOKEN="):
                token = line.split("=", 1)[1].strip()
    if not token:
        raise SystemExit("BOT_TOKEN required in .env")
    return token


def main() -> None:
    texts = load_texts()
    bot = texts["bot"]
    token = load_token()

    with httpx.Client(timeout=60.0) as c:
        r = c.post(
            API.format(token=token, method="setMyShortDescription"),
            json={"short_description": bot["short_description"]},
        )
        print("short_description", r.json())
        r = c.post(
            API.format(token=token, method="setMyDescription"),
            json={"description": bot["description"]},
        )
        print("description", r.json())
        cmds = [
            {"command": k, "description": bot["commands"][k]}
            for k in ("start", "new", "my", "profile", "help")
        ]
        r = c.post(API.format(token=token, method="setMyCommands"), json={"commands": cmds})
        print("commands", r.json())

    print("Аватар и обложка — только через @BotFather: brand/avatar.png, brand/cover.png")


if __name__ == "__main__":
    main()
