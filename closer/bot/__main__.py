import asyncio
import logging
import os
from pathlib import Path

from closer.bot.stage1_polling import bot_commands, build_stage1_bot, build_stage1_dispatcher
from closer.texts import t


def _bot_token() -> str:
    token = os.environ.get("BOT_TOKEN", "").strip()
    if token:
        return token
    env = Path(__file__).resolve().parents[2] / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("BOT_TOKEN="):
                return line.split("=", 1)[1].strip()
    return ""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    token = _bot_token()
    if not token:
        raise SystemExit("BOT_TOKEN is required")

    bot = build_stage1_bot(token)
    dp = build_stage1_dispatcher()

    me = await bot.get_me()
    logger.info("Bot @%s — этапы 1–2 (polling)", me.username)
    await bot.set_my_commands(bot_commands())
    await bot.set_my_short_description(t("bot.short_description"))
    await bot.set_my_description(t("bot.description"))
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
