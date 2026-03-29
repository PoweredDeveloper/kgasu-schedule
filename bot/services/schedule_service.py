"""In-memory cache of schedules.json + helpers for lookups and formatting."""

from __future__ import annotations

import json
import threading
import unicodedata
from html import escape as esc_html
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import config

WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

# Latin keys that students often type instead of identical-looking Cyrillic letters.
_LOOKALIKE = str.maketrans(
    {
        "A": "А",
        "a": "а",
        "B": "В",
        "b": "в",
        "C": "С",
        "c": "с",
        "E": "Е",
        "e": "е",
        "H": "Н",
        "h": "н",
        "K": "К",
        "k": "к",
        "M": "М",
        "m": "м",
        "O": "О",
        "o": "о",
        "P": "Р",
        "p": "р",
        "T": "Т",
        "t": "т",
        "X": "Х",
        "x": "х",
        "Y": "У",
        "y": "у",
    }
)

_store_lock = threading.Lock()
_groups: dict[str, dict] = {}
_mtime: float = 0.0


def normalize_group_input(s: str) -> str:
    s = unicodedata.normalize("NFKC", (s or "").strip())
    return s.translate(_LOOKALIKE)


def reload_from_disk() -> bool:
    global _groups, _mtime
    path: Path = config.SCHEDULES_PATH
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except FileNotFoundError:
        with _store_lock:
            _groups = {}
            _mtime = 0.0
        return False
    except (json.JSONDecodeError, OSError):
        return False

    if isinstance(data, dict) and "groups" in data:
        groups = data["groups"]
    elif isinstance(data, dict):
        groups = {k: v for k, v in data.items() if k != "meta" and isinstance(v, dict)}
    else:
        groups = {}

    if not isinstance(groups, dict):
        groups = {}

    try:
        m = path.stat().st_mtime
    except OSError:
        m = 0.0

    with _store_lock:
        _groups = groups
        _mtime = m
    return True


def file_mtime() -> float:
    try:
        return config.SCHEDULES_PATH.stat().st_mtime
    except OSError:
        return 0.0


def get_all_groups() -> list[str]:
    with _store_lock:
        names = [k for k, v in _groups.items() if isinstance(v, dict)]
    return sorted(names, key=lambda x: x.casefold())


def suggest_groups(user_input: str, limit: int = 6) -> list[str]:
    """Fuzzy hints when exact group is missing (e.g. 25СЖ01 not scraped yet but 24СЖ01 exists)."""
    import re

    q = normalize_group_input(user_input).casefold().replace(" ", "")
    if len(q) < 2:
        return []
    core = re.sub(r"^\d+", "", q)
    names = get_all_groups()
    scored: list[tuple[int, str]] = []
    for name in names:
        nn = normalize_group_input(name).casefold().replace(" ", "")
        if q == nn:
            continue
        rank = 99
        if q in nn or nn in q:
            rank = 0
        elif len(core) >= 3 and core in nn:
            rank = 1
        if rank < 99:
            scored.append((rank, len(name), name))
    scored.sort(key=lambda x: (x[0], x[1]))
    out: list[str] = []
    seen: set[str] = set()
    for _, _, name in scored:
        if name not in seen:
            seen.add(name)
            out.append(name)
        if len(out) >= limit:
            break
    return out


def resolve_group_canonical(user_input: str) -> str | None:
    """Match typed group to cache key (case-insensitive + Latin/Cyrillic lookalikes)."""
    q = normalize_group_input(user_input).casefold()
    if not q:
        return None
    with _store_lock:
        for name in _groups:
            if not isinstance(_groups.get(name), dict):
                continue
            if normalize_group_input(name).casefold() == q:
                return name
    return None


def _day_map(group: str) -> dict[str, list[dict]]:
    with _store_lock:
        g = _groups.get(group)
    if not isinstance(g, dict):
        return {d: [] for d in WEEKDAYS}
    return {d: list(g.get(d) or []) if isinstance(g.get(d), list) else [] for d in WEEKDAYS}


def get_schedule(group: str) -> dict[str, list[dict]]:
    return _day_map(group)


def count_lessons(group: str) -> int:
    return sum(len(get_schedule(group).get(d, [])) for d in WEEKDAYS)


def get_doc_url(group: str) -> str | None:
    with _store_lock:
        g = _groups.get(group)
    if not isinstance(g, dict):
        return None
    u = g.get("doc_url")
    return u if isinstance(u, str) and u else None


def _weekday_key_for_date(d) -> str:
    return WEEKDAYS[d.weekday()]


def get_today(group: str) -> list[dict]:
    z = ZoneInfo(config.TZ)
    now = datetime.now(z)
    key = _weekday_key_for_date(now.date())
    return _day_map(group).get(key, [])


def get_tomorrow(group: str) -> list[dict]:
    z = ZoneInfo(config.TZ)
    now = datetime.now(z)
    t = now.date() + timedelta(days=1)
    key = _weekday_key_for_date(t)
    return _day_map(group).get(key, [])


def format_lesson_line_html(les: dict) -> str:
    t = esc_html((les.get("time") or "").strip())
    subj = esc_html((les.get("subject") or "").strip())
    room = esc_html((les.get("room") or "").strip())
    teacher = esc_html((les.get("teacher") or "").strip())
    if t and subj:
        line = f"<b>{t}</b> — {subj}"
    elif subj:
        line = subj
    else:
        line = "—"
    if room:
        line += f" <i>(ауд. {room})</i>"
    if teacher:
        line += f"\n<i>{teacher}</i>"
    return line


def build_full_schedule_txt(group: str) -> str:
    import bot.texts as T

    lines: list[str] = []
    for d in WEEKDAYS:
        lines.append(T.DAY_LABEL_RU.get(d, d))
        lines.append("")
        lessons = get_schedule(group).get(d) or []
        if not lessons:
            lines.append("—")
        else:
            for les in lessons:
                t = (les.get("time") or "").strip()
                subj = (les.get("subject") or "").strip()
                lines.append(f"{t} {subj}".strip() if t else subj)
        lines.append("")
    doc = get_doc_url(group)
    if doc:
        lines.append(f"Файл на сайте: {doc}")
    return "\n".join(lines).strip()


def split_telegram_chunks(text: str, limit: int = 3800) -> list[str]:
    if len(text) <= limit:
        return [text] if text else []
    parts: list[str] = []
    buf: list[str] = []
    size = 0
    for para in text.split("\n\n"):
        block = para + "\n\n"
        if size + len(block) > limit and buf:
            parts.append("".join(buf).rstrip())
            buf = []
            size = 0
        if len(block) > limit:
            for i in range(0, len(block), limit):
                parts.append(block[i : i + limit])
            continue
        buf.append(block)
        size += len(block)
    if buf:
        parts.append("".join(buf).rstrip())
    return parts
