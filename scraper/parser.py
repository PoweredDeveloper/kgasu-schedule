"""HTML helpers for the Bitrix schedule page."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def _is_schedule_file_href(href: str) -> bool:
    h = href.lower().split("?", 1)[0]
    return h.endswith(".doc") or h.endswith(".docx")


def group_names_from_schedule_link_label(label: str) -> list[str]:
    """Split listing link text into group ids; strip trailing .doc / .docx."""
    names: list[str] = []
    for part in label.replace(";", ",").split(","):
        g = part.strip()
        for ext in (".docx", ".doc"):
            if g.lower().endswith(ext):
                g = g[: -len(ext)].strip()
                break
        if g:
            names.append(g)
    return names


def extract_doc_links(html: str, base_url: str) -> list[tuple[str, str]]:
    """Collect .doc and .docx attachments (KGASU increasingly uses .docx for new groups)."""
    soup = BeautifulSoup(html, "html.parser")
    out: list[tuple[str, str]] = []
    for a in soup.select(".news-list a[href]"):
        href = (a.get("href") or "").strip()
        if not _is_schedule_file_href(href):
            continue
        text = (a.get_text() or "").strip()
        if not text:
            continue
        out.append((urljoin(base_url, href), text))
    return out


def extract_max_listing_page(html: str) -> int:
    """Bitrix uses PAGEN_1=… on listing pages; default single page if no pager."""
    m = 1
    for a in BeautifulSoup(html, "html.parser").select('a.pagination[href*="PAGEN_1="]'):
        href = a.get("href") or ""
        found = re.findall(r"PAGEN_1=(\d+)", href)
        for x in found:
            m = max(m, int(x))
    return m
