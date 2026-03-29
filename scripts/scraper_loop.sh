#!/bin/sh
# Runs `python -m scraper.scraper`, then sleeps SCRAPE_INTERVAL_SEC (default 6h), forever.
# Used by the `scraper-scheduler` Compose service (profile `scheduler`).

INTERVAL="${SCRAPE_INTERVAL_SEC:-21600}"

while true; do
  echo "[scraper-scheduler] $(date -Is) starting scraper"
  python -m scraper.scraper || echo "[scraper-scheduler] scraper exited with $?"
  echo "[scraper-scheduler] sleeping ${INTERVAL}s until next run"
  sleep "$INTERVAL"
done
