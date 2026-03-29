"""Scrape listing pages (with Bitrix pagination), .doc / .docx files, write schedules.json."""

from __future__ import annotations

import json
import logging
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from scraper.doc_parse import WEEKDAYS, parse_schedule_from_antiword, plain_text_from_schedule_file
from scraper.parser import (
    extract_doc_links,
    extract_max_listing_page,
    group_names_from_schedule_link_label,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def _delay() -> None:
    time.sleep(config.REQUEST_DELAY_SEC + random.uniform(0, 0.35))


def _fetch(client: httpx.Client, params: list[tuple[str, str]]) -> str:
    url = f"{config.SCRAPE_BASE_URL}?{urlencode(params)}"
    last_err: Exception | None = None
    for attempt in range(config.REQUEST_RETRIES):
        try:
            r = client.get(url, follow_redirects=True, timeout=60.0)
            r.raise_for_status()
            _delay()
            return r.text
        except Exception as e:
            last_err = e
            wait = 2**attempt + random.uniform(0, 0.5)
            logger.warning("fetch attempt %s failed: %s (sleep %.1fs)", attempt + 1, e, wait)
            time.sleep(wait)
    assert last_err is not None
    raise last_err


def _build_filter_params(*, kurs: str, institut: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = [("arrFilter_ff[NAME]", "")]
    if (v := config.SCRAPE_TIP_RASP.strip()):
        pairs.append(("arrFilter_pf[TIP_RASP]", v))
    if (v := config.SCRAPE_UCH_GOD.strip()):
        pairs.append(("arrFilter_pf[UCH_GOD]", v))
    if (v := config.SCRAPE_SEMESTR.strip()):
        pairs.append(("arrFilter_pf[SEMESTR]", v))
    if kurs:
        pairs.append(("arrFilter_pf[KURS]", kurs))
    if institut:
        pairs.append(("arrFilter_pf[INSTITUT]", institut))
    pairs.extend([("set_filter", "Искать"), ("set_filter", "Y")])
    return pairs


def _build_filter_params_semester_only() -> list[tuple[str, str]]:
    """Match site behaviour «все» except semester — surfaces .docx like 25СЖ01,25СЖ02."""
    pairs: list[tuple[str, str]] = [("arrFilter_ff[NAME]", "")]
    if (v := config.SCRAPE_SEMESTR.strip()):
        pairs.append(("arrFilter_pf[SEMESTR]", v))
    pairs.extend([("set_filter", "Искать"), ("set_filter", "Y")])
    return pairs


def _discover_urls(client: httpx.Client) -> tuple[dict[str, set[str]], int]:
    url_to_groups: dict[str, set[str]] = {}
    listing_http_count = 0

    def add_from_html(html: str) -> None:
        for href, label in extract_doc_links(html, config.SCRAPE_BASE_URL):
            names = group_names_from_schedule_link_label(label)
            for g in names:
                url_to_groups.setdefault(href, set()).add(g)

    def listing_fetch(pairs: list[tuple[str, str]], label: str, page: int, pages: int) -> str:
        nonlocal listing_http_count
        listing_http_count += 1
        html = _fetch(client, pairs)
        logger.info(
            "[%s] listing %s page %s/%s — %s unique schedule files",
            listing_http_count,
            label,
            page,
            pages,
            len(url_to_groups),
        )
        return html

    def ingest_listing(pairs: list[tuple[str, str]], label: str) -> None:
        nonlocal listing_http_count
        try:
            listing_http_count += 1
            first = _fetch(client, pairs)
            add_from_html(first)
            last_page = extract_max_listing_page(first)
            logger.info(
                "[%s] listing %s page 1/%s — %s unique schedule files",
                listing_http_count,
                label,
                last_page,
                len(url_to_groups),
            )
            for p in range(2, last_page + 1):
                add_from_html(
                    listing_fetch(
                        pairs + [("PAGEN_1", str(p))],
                        label,
                        p,
                        last_page,
                    )
                )
        except Exception as e:
            logger.error("listing %s: %s", label, e)

    ingest_listing(
        _build_filter_params_semester_only(),
        "semester-only (all types/years/courses — catches .docx)",
    )
    ingest_listing(_build_filter_params(kurs="", institut=""), "broad year+sem+type")

    for kid in config.KURS_IDS:
        k = kid.strip()
        if not k:
            continue
        ingest_listing(_build_filter_params(kurs=k, institut=""), f"kurs={k}")

    for iid in config.INSTITUT_IDS:
        inst = iid.strip()
        if not inst:
            continue
        for kid in config.KURS_IDS:
            k = kid.strip()
            if not k:
                continue
            ingest_listing(
                _build_filter_params(kurs=k, institut=inst),
                f"kurs={k} inst={inst}",
            )

    return url_to_groups, listing_http_count


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def run() -> None:
    out_path = config.SCHEDULES_PATH
    headers = {"User-Agent": config.USER_AGENT}
    groups_out: dict[str, dict] = {}

    if config.SCRAPE_SKIP_PARSE:
        logger.info(
            "SCRAPE_SKIP_PARSE: after discovery, only doc_url is stored (no download / extract / parse)"
        )

    with httpx.Client(headers=headers) as client:
        url_to_groups, n_listing_http = _discover_urls(client)
        n_urls = len(url_to_groups)
        total_steps = n_listing_http + n_urls
        logger.info(
            "discovery done: %s listing requests, %s unique schedule files → total steps %s",
            n_listing_http,
            n_urls,
            total_steps,
        )

        sorted_items = sorted(url_to_groups.items(), key=lambda x: x[0])
        empty = {d: [] for d in WEEKDAYS}
        for i, (url, gnames) in enumerate(sorted_items, start=1):
            step = n_listing_http + i
            if config.SCRAPE_SKIP_PARSE:
                logger.info("[%s/%s] record url (parse skipped) %s", step, total_steps, url)
                for g in sorted(gnames):
                    groups_out[g] = dict(empty) | {"doc_url": url}
                continue

            logger.info("[%s/%s] download & parse %s", step, total_steps, url)
            try:
                r = client.get(url, follow_redirects=True, timeout=120.0)
                r.raise_for_status()
                raw = r.content
            except Exception as e:
                logger.error("[%s/%s] download failed: %s", step, total_steps, e)
                for g in sorted(gnames):
                    groups_out[g] = {d: [] for d in WEEKDAYS} | {"doc_url": url, "parse_error": str(e)}
                _delay()
                continue

            _delay()
            text = plain_text_from_schedule_file(url, raw)
            if not text.strip():
                sched = {d: [] for d in WEEKDAYS}
                for g in sorted(gnames):
                    groups_out[g] = sched | {"doc_url": url, "parse_error": "extract_empty"}
                continue

            sched = parse_schedule_from_antiword(text)
            if sum(len(sched[d]) for d in WEEKDAYS) == 0:
                logger.warning("parser produced 0 lessons for %s", url)
            for g in sorted(gnames):
                groups_out[g] = dict(sched) | {"doc_url": url}

    meta: dict = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "source_url": config.SCRAPE_BASE_URL,
        "groups_count": len(groups_out),
    }
    if config.SCRAPE_SKIP_PARSE:
        meta["parse_skipped"] = True

    payload = {
        "schema_version": 1,
        "meta": meta,
        "groups": groups_out,
    }
    _atomic_write_json(out_path, payload)
    logger.info("wrote %s (%s groups)", out_path, len(groups_out))


if __name__ == "__main__":
    run()
