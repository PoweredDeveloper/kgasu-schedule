"""Tests for schedule cache and formatting (no Telegram)."""

from __future__ import annotations

import json

import pytest

import config
from bot.services import schedule_service


@pytest.fixture(autouse=True)
def _reset_schedule_cache(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Each test uses an isolated schedules file and reloads the in-memory store."""
    path = tmp_path / "schedules.json"
    monkeypatch.setattr(config, "SCHEDULES_PATH", path)
    path.write_text('{"schema_version":1,"meta":{},"groups":{}}', encoding="utf-8")
    schedule_service.reload_from_disk()


def test_normalize_group_input_lookalikes() -> None:
    assert schedule_service.normalize_group_input("25AB01") == "25АВ01"


def test_reload_from_disk_and_resolve_group(tmp_path, monkeypatch) -> None:
    path = tmp_path / "schedules.json"
    monkeypatch.setattr(config, "SCHEDULES_PATH", path)
    payload = {
        "groups": {
            "25СЖ01": {
                "Monday": [
                    {
                        "time": "10:00-11:00",
                        "subject": "Лекция",
                        "teacher": "",
                        "room": "101",
                    }
                ],
                "doc_url": "https://example.com/f.docx",
            }
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert schedule_service.reload_from_disk()
    assert schedule_service.resolve_group_canonical("25сж01") == "25СЖ01"
    assert schedule_service.get_doc_url("25СЖ01") == "https://example.com/f.docx"
    assert schedule_service.count_lessons("25СЖ01") == 1


def test_suggest_groups() -> None:
    path = config.SCHEDULES_PATH
    path.write_text(
        json.dumps({"groups": {"24СЖ01": {}, "25СЖ02": {}}}),
        encoding="utf-8",
    )
    schedule_service.reload_from_disk()
    hints = schedule_service.suggest_groups("25СЖ01", limit=5)
    # Same programme suffix «сж01» matches 24СЖ01 stronger than 25СЖ02 («сж02»).
    assert "24СЖ01" in hints


def test_format_lesson_line_html_escapes() -> None:
    line = schedule_service.format_lesson_line_html(
        {"time": "1<2", "subject": "A&B", "room": "", "teacher": ""}
    )
    assert "&lt;" in line
    assert "A&amp;B" in line


def test_split_telegram_chunks() -> None:
    assert schedule_service.split_telegram_chunks("") == []
    short = "hello"
    assert schedule_service.split_telegram_chunks(short) == ["hello"]
    big = "x" * 100
    parts = schedule_service.split_telegram_chunks(big, limit=30)
    assert len(parts) > 1
    assert "".join(parts).replace("\n", "") == big
