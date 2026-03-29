"""Persist each user's chosen group on disk (survives /start and bot restarts)."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import config

_lock = threading.Lock()
_path: Path = config.USER_PREFS_PATH


def _load_raw() -> dict:
    try:
        return json.loads(_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def get_group(user_id: int) -> str | None:
    with _lock:
        data = _load_raw()
    v = data.get(str(user_id))
    return v if isinstance(v, str) and v.strip() else None


def set_group(user_id: int, group: str) -> None:
    with _lock:
        data = _load_raw()
        data[str(user_id)] = group.strip()
        _path.parent.mkdir(parents=True, exist_ok=True)
        tmp = _path.with_suffix(_path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(_path)


def clear_group(user_id: int) -> None:
    with _lock:
        data = _load_raw()
        data.pop(str(user_id), None)
        if not data:
            try:
                _path.unlink(missing_ok=True)
            except OSError:
                pass
            return
        tmp = _path.with_suffix(_path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(_path)
