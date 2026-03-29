"""Точка входа Telegram-бота."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import config
from bot.handlers import setup_routers
from bot.services import schedule_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logging.getLogger("aiogram.event").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def _mtime_poll_loop() -> None:
    last = schedule_service.file_mtime()
    while True:
        await asyncio.sleep(config.SCHEDULE_POLL_SEC)
        m = schedule_service.file_mtime()
        if m > last:
            if schedule_service.reload_from_disk():
                logger.info("Reloaded schedules.json (file changed)")
            last = m


async def main() -> None:
    if not config.BOT_TOKEN:
        logger.error("Set BOT_TOKEN in environment or .env")
        sys.exit(1)

    schedule_service.reload_from_disk()
    if not schedule_service.get_all_groups():
        logger.warning("schedules.json missing or empty — bot will show onboarding errors")

    bot = Bot(config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(setup_routers())

    asyncio.create_task(_mtime_poll_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
