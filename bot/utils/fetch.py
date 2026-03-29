"""Small network helper for the bot (no scraping — only fetching known .doc URLs)."""

from __future__ import annotations

import asyncio

import httpx

import config


async def download_bytes(url: str) -> bytes:
    def _sync() -> bytes:
        with httpx.Client(
            timeout=120.0,
            follow_redirects=True,
            headers={"User-Agent": config.USER_AGENT},
        ) as c:
            r = c.get(url)
            r.raise_for_status()
            return r.content

    return await asyncio.to_thread(_sync)
