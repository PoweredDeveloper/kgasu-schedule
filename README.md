# KGASU Schedule Telegram Bot

Telegram bot for students of **Kazan State University of Architecture and Engineering (КГАСУ)**. A **scraper** walks the Bitrix listing and writes `data/schedules.json` with **group names and `doc_url` only** (no Word download, no parsing). When a student taps **Today**, **Tomorrow**, or **Full schedule**, the **bot** downloads that group’s `.doc` / `.docx` from the university CDN, runs **antiword** / **python-docx**, parses rows into weekdays, and replies (with week-parity filtering). Picking a group or reloading the cache does not hit the file URLs-only those button actions do.

User-facing text in the bot is **Russian**. Technical docs here are in English.

## Features

- Remembered group per Telegram user (`data/user_groups.json`)
- Pick group from a paginated list or type it manually (case-insensitive; common Latin/Cyrillic lookalikes normalized)
- Full schedule as **`.txt`** (parsed on demand) or the official **Word** attachment if parsing fails
- Today / tomorrow (Europe/Moscow): fetch + parse on each tap
- Week parity (even/odd) from the **calendar** (ISO week in `TZ`), not from the website
- Optional service menu: help, reload cache from disk

See `PLAN.md` for the original design notes.

## Requirements

- Docker and Docker Compose (recommended)
- A Telegram **bot token** from [@BotFather](https://t.me/BotFather)
- **[uv](https://docs.astral.sh/uv/)** for local installs and tests (optional if you only use Docker)

## Quick start (Docker)

1. Copy environment template and set the token:

   ```bash
   cp .env.example .env
   # edit .env - set BOT_TOKEN=...
   ```

2. Build the image (first time or after code changes):

   ```bash
   docker compose build
   ```

3. **Schedule cache (`data/schedules.json`)**

   **Recommended - automatic scraper in Docker** (no host `cron`):

   ```bash
   docker compose --profile scheduler up -d
   ```

   Starts the **bot** (no profile) and **`scraper-scheduler`**: runs a full scrape, then sleeps **`SCRAPE_INTERVAL_SEC`** (default **21600** = 6 hours), repeats forever.

   **One-off scrape** (e.g. right after changing `.env` filters):

   ```bash
   docker compose --profile manual run --rm scraper
   ```

   Adjust `SCRAPE_UCH_GOD`, `SCRAPE_SEMESTR`, and related IDs in `.env` if the site’s filter values change. Leaving `SCRAPE_TIP_RASP`, `SCRAPE_UCH_GOD`, or `SCRAPE_SEMESTR` **empty** omits that filter (same idea as “(все)” on the site). The scraper only performs **HTTP requests to the listing**; tune politeness with `SCRAPE_LISTING_DELAY_SEC` (default 0.5s).

4. **Run the bot** (if you did not already start it with the scheduler):

   ```bash
   docker compose up -d bot
   ```

The `./data` folder is mounted into the containers so the bot, manual scraper, and scheduler share `schedules.json` and user preference files.

## Environment variables

| Variable                   | Purpose                                                                                                            |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `BOT_TOKEN`                | Telegram bot token (**required** for the bot)                                                                      |
| `SCHEDULES_PATH`           | Path to `schedules.json` (default `data/schedules.json`; Compose sets `/app/data/schedules.json` in the container) |
| `USER_PREFS_PATH`          | Path to per-user saved group JSON (default `data/user_groups.json`)                                                |
| `SCRAPE_*`                 | Bitrix filter IDs for the scraper (see `.env.example`). Empty value = omit that filter.                            |
| `SCRAPE_LISTING_DELAY_SEC` | Seconds after each **listing** page on the main site (default **0.5**). Legacy alias: `SCRAPE_DELAY_SEC`.          |
| `SCHEDULE_POLL_SEC`        | How often the bot checks whether `schedules.json` changed on disk                                                  |
| `SCHEDULE_RELOAD_SEC`      | Periodic full reload of JSON (see `.env.example`)                                                                  |
| `TZ`                       | Timezone for “today” / “tomorrow” (default `Europe/Moscow`)                                                        |
| `GROUPS_PAGE_SIZE`         | Groups per page in the inline list (optional)                                                                      |
| `SCRAPE_INTERVAL_SEC`      | **Scheduler service only:** seconds to sleep after each scrape before the next run (default **21600** = 6 h).      |

## Project layout

```
├── bot/                   # aiogram v3 bot
├── scraper/               # Bitrix listing → doc_url index (Word parse lives in bot path via scraper.doc_parse)
├── tests/                 # pytest
├── data/                  # schedules.json, user_groups.json (not committed)
├── .github/workflows/     # CI (pytest)
├── config.py
├── docker-compose.yml
├── scripts/               # scraper_loop.sh (Docker scheduler)
├── Dockerfile
├── pyproject.toml         # dependencies (managed by uv)
├── uv.lock                # lockfile - commit this
├── .python-version        # 3.12 (used by uv locally)
├── pytest.ini
├── PLAN.md
└── README.md
```

## Tests and CI

```bash
uv sync --group dev
uv run pytest
```

After changing dependencies in `pyproject.toml`, refresh the lockfile: `uv lock` (then commit `uv.lock`).

GitHub Actions runs `uv sync --frozen --group dev` and `uv run pytest` on push and pull requests (Python 3.12).

## Local development (without Docker)

Use **uv** from the repository root (`.python-version` pins 3.12). The **scraper** only hits listing pages (no antiword). The **bot** needs **antiword** on `PATH` for on-demand `.doc` parsing; `.docx` uses python-docx.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # once: https://docs.astral.sh/uv/getting-started/installation/
uv sync
cp .env.example .env
uv run python -m scraper.scraper   # listing → schedules.json (doc_url only)
uv run python -m bot.main         # antiword required when users open schedules for .doc groups
```

With dev tools (pytest): `uv sync --group dev`.

## My group is missing (e.g. `25…` but only `24…` in the bot)

The bot only knows groups that appear in **`data/schedules.json`**. New groups are often published as **`.docx`**; use a current scraper build, re-run the full scraper, and align `.env` filters with what you use on the website (year, semester, optional broad filters).

You can **type the group name in chat** while browsing the list; if it is still not found, the bot will suggest similar names from the cache and remind you to refresh the scraper.

## Updating schedules

Prefer **`docker compose --profile scheduler up -d`** so **`scraper-scheduler`** refreshes `schedules.json` on a timer inside Docker (see `SCRAPE_INTERVAL_SEC`). For a single immediate run, use `docker compose --profile manual run --rm scraper`.

The bot picks up changes when `schedules.json` is replaced or updated (mtime polling).

## License

[MIT License](/LICENSE)
