"""In-memory cache of schedules.json + lookups, on-demand fetch/parse of Word files."""

from __future__ import annotations

import asyncio
import json
import re
import threading
import unicodedata
from html import escape as esc_html
from datetime import date, datetime, timedelta
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

# Inline teacher lists in KGASU subject cells (доц. …, ст. преп. …) — strip for PE/sport only.
_RE_INLINE_TEACHER_START = re.compile(
    r"[\s,\-]+(?:"
    r"ст\.\s*преп\.|ст\.преп\.|"
    r"доц\.|проф\.|преп\.|ассист\."
    r")\s+[А-ЯЁA-Za-z]",
    re.IGNORECASE,
)


def _is_pe_or_sport_subject(subject: str) -> bool:
    """True for physical education / sport electives (not e.g. «физическая химия»)."""
    n = (subject or "").lower().replace("ё", "е")
    if "физкульт" in n:
        return True
    if "физическ" in n and "культур" in n:
        return True
    if "культур" in n and "спорт" in n:
        return True
    if "электив" in n and "спорт" in n:
        return True
    return False


def display_subject(subject: str) -> str:
    """For PE/sport rows, drop inline teacher names after academic titles (short Telegram lines)."""
    s = (subject or "").strip()
    if not s or not _is_pe_or_sport_subject(s):
        return s
    m = _RE_INLINE_TEACHER_START.search(s)
    if not m:
        return s
    return s[: m.start()].rstrip(" ,-–—")


def _lesson_subject_for_display(les: dict) -> str:
    return lesson_course_and_teachers_blob(les)[0]


def lesson_course_and_teachers_blob(les: dict) -> tuple[str, str]:
    """Course title vs inline teacher list from subject cell (PE: teachers hidden)."""
    raw = (les.get("subject") or "").strip()
    if not raw:
        return "", ""
    if _is_pe_or_sport_subject(raw):
        return display_subject(raw), ""
    m = _RE_INLINE_TEACHER_START.search(raw)
    if not m:
        return raw, ""
    course = raw[: m.start()].rstrip(" ,-–—")
    blob = raw[m.start() :].lstrip(" ,-–—")
    return course, blob


def split_teacher_entries(blob: str) -> list[str]:
    """Split «доц. …, ст. преп. …» tail into separate entries."""
    b = (blob or "").strip()
    if not b:
        return []
    title = r"(?:ст\.\s*преп\.|ст\.преп\.|доц\.|проф\.|преп\.|ассист\.)"
    pat = re.compile(title + r"\s+.+?(?=(?:\s*,\s*|\s+)" + title + r"|\Z)", re.UNICODE | re.DOTALL)
    entries = [m.group(0).strip() for m in pat.finditer(b)]
    return entries if entries else [b]


def format_teachers_blob_display(blob: str) -> str:
    """Show one or two professors in full; skip listing three or more (collapse to «и др.»)."""
    entries = split_teacher_entries(blob)
    if not entries:
        return ""
    if len(entries) == 1:
        return entries[0]
    if len(entries) == 2:
        return f"{entries[0]}, {entries[1]}"
    return f"{entries[0]}, {entries[1]} и др."


def lesson_teacher_line_for_display(les: dict) -> str:
    """Text for teacher line: inline blob (collapsed) or legacy teacher field."""
    _, blob = lesson_course_and_teachers_blob(les)
    out = format_teachers_blob_display(blob)
    if out:
        return out
    legacy = (les.get("teacher") or "").strip()
    return legacy

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


def split_group_name(group: str) -> tuple[str, str, str] | None:
    """Split group into year/prefix/number, e.g. 25СЖ01 -> ('25', 'СЖ', '01')."""
    s = normalize_group_input(group).strip()
    m = re.match(r"^(\d{2})([A-Za-zА-Яа-яЁё]+)(\d+)$", s)
    if not m:
        return None
    year, prefix, number = m.groups()
    return year, prefix.upper(), number


def get_group_years() -> list[str]:
    years: set[str] = set()
    for g in get_all_groups():
        parts = split_group_name(g)
        if parts:
            years.add(parts[0])
    return sorted(years, key=int, reverse=True)


def get_prefixes_for_year(year: str) -> list[str]:
    prefixes: set[str] = set()
    for g in get_all_groups():
        parts = split_group_name(g)
        if not parts:
            continue
        gy, pref, _ = parts
        if gy == year:
            prefixes.add(pref)
    return sorted(prefixes, key=lambda x: x.casefold())


def get_groups_for_year_prefix(year: str, prefix: str) -> list[str]:
    out: list[tuple[int, str]] = []
    want_prefix = normalize_group_input(prefix).upper()
    for g in get_all_groups():
        parts = split_group_name(g)
        if not parts:
            continue
        gy, pref, num = parts
        if gy == year and pref == want_prefix:
            out.append((int(num), g))
    out.sort(key=lambda x: x[0])
    return [g for _, g in out]


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
    """Cached weekday lists are empty when using doc_url-only scraper; prefer async loaders."""
    return _day_map(group)


def group_has_schedule_file(group: str) -> bool:
    """True if the group has a doc_url (bot can fetch and parse on demand)."""
    return get_doc_url(group) is not None


def get_doc_url(group: str) -> str | None:
    with _store_lock:
        g = _groups.get(group)
    if not isinstance(g, dict):
        return None
    u = g.get("doc_url")
    return u if isinstance(u, str) and u else None


def _weekday_key_for_date(d) -> str:
    return WEEKDAYS[d.weekday()]


def calendar_week_parity_for_date(d: date) -> str:
    """
    Map calendar date → table column «Чет» / «Неч» (stored as week_parity even/odd).

    KGASU week numbering does not match raw ISO parity: use **inverted** ISO parity so the
    banner («чётная»/«нечётная») and filtered rows stay aligned with the site’s tables.
    """
    _, iso_week, _ = d.isocalendar()
    # Even ISO week → «нечётная» / Неч; odd ISO week → «чётная» / Чет
    return "odd" if iso_week % 2 == 0 else "even"


def _lessons_for_calendar_week(lessons: list[dict], ref: date) -> list[dict]:
    want = calendar_week_parity_for_date(ref)
    out: list[dict] = []
    for les in lessons:
        p = les.get("week_parity")
        if p not in ("even", "odd") or p == want:
            out.append(les)
    return out


async def load_parsed_week(group: str) -> tuple[dict[str, list[dict]] | None, str | None]:
    """
    Download group's schedule file and parse into weekday -> lessons.
    Returns (schedule, None) or (None, error_code): no_doc_url, download_failed, extract_empty.
    """
    url = get_doc_url(group)
    if not url:
        return None, "no_doc_url"
    try:
        from bot.utils.fetch import download_bytes

        raw = await download_bytes(url)
    except Exception:
        return None, "download_failed"

    def _parse() -> tuple[dict[str, list[dict]] | None, str | None]:
        from scraper.doc_parse import parse_schedule_from_antiword, plain_text_from_schedule_file

        text = plain_text_from_schedule_file(url, raw)
        if not text.strip():
            return None, "extract_empty"
        return parse_schedule_from_antiword(text), None

    return await asyncio.to_thread(_parse)


async def lessons_for_date_async(group: str, d: date) -> tuple[list[dict], str | None]:
    """Lessons for calendar date `d` with week-parity filter. Error code only on fetch/parse failure."""
    full, err = await load_parsed_week(group)
    if err:
        return [], err
    assert full is not None
    key = _weekday_key_for_date(d)
    raw_list = full.get(key, [])
    return _lessons_for_calendar_week(raw_list, d), None


async def build_full_schedule_txt_async(group: str) -> tuple[str, str | None]:
    """Build .txt for all weekdays (parity-filtered for current ISO week)."""
    full, err = await load_parsed_week(group)
    if err:
        return "", err
    assert full is not None

    z = ZoneInfo(config.TZ)
    ref = datetime.now(z).date()
    body = _build_week_txt(full, ref)
    doc = get_doc_url(group)
    if doc:
        body += f"\n\nФайл на сайте: {doc}"
    return body.strip(), None


def _build_week_txt(full: dict[str, list[dict]], ref: date) -> str:
    import bot.texts as T

    lines: list[str] = []
    for i, day in enumerate(WEEKDAYS):
        lines.append(T.DAY_LABEL_RU.get(day, day))
        lines.append("")
        lessons = _lessons_for_calendar_week(full.get(day) or [], ref)
        if not lessons:
            lines.append("-")
        else:
            for j, les in enumerate(lessons):
                t = (les.get("time") or "").strip()
                course, blob = lesson_course_and_teachers_blob(les)
                teach = format_teachers_blob_display(blob)
                if not teach:
                    teach = (les.get("teacher") or "").strip()
                if t and course:
                    main = f"{t} - {course}"
                elif course:
                    main = course
                else:
                    main = "-"
                lines.append(main)
                if teach:
                    lines.append(f"    {teach}")
                if j < len(lessons) - 1:
                    lines.append("")
        lines.append("")
        if i < len(WEEKDAYS) - 1:
            lines.append("--------------------")
            lines.append("")
    return "\n".join(lines).rstrip()


def format_lesson_line_html(les: dict) -> str:
    t = esc_html((les.get("time") or "").strip())
    subj = esc_html(_lesson_subject_for_display(les))
    room = esc_html((les.get("room") or "").strip())
    teacher_raw = lesson_teacher_line_for_display(les)
    if _is_pe_or_sport_subject((les.get("subject") or "").strip()):
        teacher_raw = ""
    teacher = esc_html(teacher_raw)
    if t and subj:
        line = f"<b>{t}</b> - {subj}"
    elif subj:
        line = subj
    else:
        line = "-"
    if room:
        line += f" <i>(ауд. {room})</i>"
    if teacher:
        line += f"\n<i>{teacher}</i>"
    return line


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
