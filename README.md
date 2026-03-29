# KGASU Schedule Telegram Bot

Telegram bot for students of **Kazan State University of Architecture and Engineering (КГАСУ)**. It serves class schedules from a **local cache** built by a separate scraper. The university site uses Bitrix filters and publishes timetables as **Word `.doc` and `.docx`** files. The scraper walks listing pages, collects links, downloads each file, extracts plain text (**antiword** for legacy `.doc`, **python-docx** for `.docx`), parses rows into weekdays, and writes `data/schedules.json`. The bot never hits the university website during normal chats.

User-facing text in the bot is **Russian**. Technical docs here are in English.

## Features

- Remembered group per Telegram user (`data/user_groups.json`)
- Pick group from a paginated list or type it manually (case-insensitive; common Latin/Cyrillic lookalikes normalized)
- Full schedule as a **`.txt` file** when parsed lessons exist; otherwise the bot sends or links the official **Word file** from the site (`.doc` / `.docx`)
- Today / tomorrow (Europe/Moscow), when parsed data exists
- Week parity (even/odd) from the **calendar** (ISO week in `TZ`), not from the website
- Optional service menu: help, reload cache from disk

See `PLAN.md` for the original design notes.

## Requirements

- Docker and Docker Compose (recommended)
- A Telegram **bot token** from [@BotFather](https://t.me/BotFather)

## Quick start (Docker)

1. Copy environment template and set the token:

   ```bash
   cp .env.example .env
   # edit .env — set BOT_TOKEN=...
   ```

2. Build the image (first time or after code changes):

   ```bash
   docker compose build
   ```

3. **Build the schedule cache** (run after semester/year changes or periodically, e.g. cron):

   ```bash
   docker compose --profile manual run --rm scraper
   ```

   This writes `data/schedules.json`. Adjust `SCRAPE_UCH_GOD`, `SCRAPE_SEMESTR`, and related IDs in `.env` if the site’s filter values change. Leaving `SCRAPE_TIP_RASP`, `SCRAPE_UCH_GOD`, or `SCRAPE_SEMESTR` **empty** omits that filter (same idea as “(все)” on the site).

   **Discovery only (no download / no parsing):** fast pass that still records every group and `doc_url` — useful when you only need links or want to avoid antiword noise for broken files:

   ```bash
   SCRAPE_SKIP_PARSE=1 docker compose --profile manual run --rm scraper
   ```

   With `parse_skipped` set in `meta`, weekday lists stay empty until you run a full scrape without that flag.

4. **Run the bot**:

   ```bash
   docker compose up -d bot
   ```

The `./data` folder is mounted into the container so both the scraper and the bot share `schedules.json` and user preference files.

## Environment variables

| Variable              | Purpose                                                                                                            |
| --------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `BOT_TOKEN`           | Telegram bot token (**required** for the bot)                                                                    |
| `SCHEDULES_PATH`      | Path to `schedules.json` (default `data/schedules.json`; Compose sets `/app/data/schedules.json` in the container) |
| `USER_PREFS_PATH`     | Path to per-user saved group JSON (default `data/user_groups.json`)                                                |
| `SCRAPE_*`            | Bitrix filter IDs for the scraper (see `.env.example`). Empty value = omit that filter.                            |
| `SCRAPE_SKIP_PARSE`   | If `1` / `true` / `yes` / `on`: after listing discovery, store only `doc_url` and empty weekdays (no file download or parse). |
| `SCHEDULE_POLL_SEC`   | How often the bot checks whether `schedules.json` changed on disk                                                  |
| `SCHEDULE_RELOAD_SEC` | Periodic full reload of JSON (see `.env.example`)                                                                  |
| `TZ`                  | Timezone for “today” / “tomorrow” (default `Europe/Moscow`)                                                        |
| `GROUPS_PAGE_SIZE`    | Groups per page in the inline list (optional)                                                                    |

## Project layout

```
├── bot/                   # aiogram v3 bot
├── scraper/               # listing + .doc/.docx download + extract + parser
├── tests/                 # pytest
├── data/                  # schedules.json, user_groups.json (not committed)
├── .github/workflows/     # CI (pytest)
├── config.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt   # pytest (local / CI)
├── pytest.ini
├── PLAN.md
└── README.md
```

## Tests and CI

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

GitHub Actions runs the same on push and pull requests (Python 3.12).

## Local development (without Docker)

Install dependencies and run from the repository root. For a **full** scrape you need **antiword** on `PATH` for `.doc` files; `.docx` uses python-docx (already in `requirements.txt`). The bot only reads JSON.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m scraper.scraper   # needs antiword for .doc, or use Docker scraper
python -m bot.main
```

## My group is missing (e.g. `25…` but only `24…` in the bot)

The bot only knows groups that appear in **`data/schedules.json`**. New groups are often published as **`.docx`**; use a current scraper build, re-run the full scraper, and align `.env` filters with what you use on the website (year, semester, optional broad filters).

You can **type the group name in chat** while browsing the list; if it is still not found, the bot will suggest similar names from the cache and remind you to refresh the scraper.

## Updating schedules

Re-run the scraper container on a schedule (host cron example):

```cron
0 */6 * * * cd /path/to/kgasu-schedule && docker compose --profile manual run --rm scraper
```

The bot picks up changes when `schedules.json` is replaced or updated (mtime polling).

## License

Not specified. Add a `LICENSE` file if you distribute the project.
