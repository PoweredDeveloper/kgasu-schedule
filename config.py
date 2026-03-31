"""Load settings from environment."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent


def _path(name: str, default: str) -> Path:
    p = os.environ.get(name, default)
    return Path(p) if os.path.isabs(p) else (ROOT / p).resolve()


BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
# Optional: shown in «Поддержка» (e.g. @username or t.me/… link)
SUPPORT_CONTACT = os.environ.get("SUPPORT_CONTACT", "").strip()
SCHEDULES_PATH = _path("SCHEDULES_PATH", "data/schedules.json")
USER_PREFS_PATH = _path("USER_PREFS_PATH", "data/user_groups.json")

SCRAPE_BASE_URL = os.environ.get(
    "SCRAPE_BASE_URL", "https://www.kgasu.ru/student/raspisanie-zanyatiy/"
).rstrip("/") + "/"

SCRAPE_TIP_RASP = os.environ.get("SCRAPE_TIP_RASP", "107")
SCRAPE_UCH_GOD = os.environ.get("SCRAPE_UCH_GOD", "236")
SCRAPE_SEMESTR = os.environ.get("SCRAPE_SEMESTR", "94")

USER_AGENT = os.environ.get(
    "SCRAPE_USER_AGENT",
    "Mozilla/5.0 (compatible; KGASU-ScheduleBot/1.0; +https://www.kgasu.ru/)",
)

# Politeness delay after each **listing** HTTP response (main Bitrix site).
REQUEST_DELAY_SEC = float(
    os.environ.get(
        "SCRAPE_LISTING_DELAY_SEC",
        os.environ.get("SCRAPE_DELAY_SEC", "0.5"),
    )
)
REQUEST_RETRIES = int(os.environ.get("SCRAPE_RETRIES", "3"))

SCHEDULE_RELOAD_SEC = int(os.environ.get("SCHEDULE_RELOAD_SEC", "300"))
SCHEDULE_POLL_SEC = int(os.environ.get("SCHEDULE_POLL_SEC", "60"))

TZ = os.environ.get("TZ", "Europe/Moscow")

GROUPS_PAGE_SIZE = int(os.environ.get("GROUPS_PAGE_SIZE", "12"))

# Kurs and institute Bitrix IDs (empty kurs = skip that dimension in one pass)
KURS_IDS = os.environ.get("SCRAPE_KURS_IDS", "101,102,103,104,105,106").split(",")
INSTITUT_IDS = os.environ.get(
    "SCRAPE_INSTITUT_IDS", "109,110,111,112,113,114"
).split(",")
