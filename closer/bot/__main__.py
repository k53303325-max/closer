import asyncio
import logging

from closer.bot.stage1_polling import bot_commands, build_stage1_bot, build_stage1_dispatcher
from closer.config import get_settings
from closer.texts import t

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN is required")

    bot = build_stage1_bot(settings.bot_token)
    dp = build_stage1_dispatcher()

    me = await bot.get_me()
    logger.info("Bot @%s — этап 1 (polling)", me.username)
    await bot.set_my_commands(bot_commands())
    await bot.set_my_short_description(t("bot.short_description"))
    await bot.set_my_description(t("bot.description"))
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
