"""Tests for schedule cache and formatting (no Telegram)."""

from __future__ import annotations

import json
from datetime import date

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
                "Monday": [],
                "doc_url": "https://example.com/f.docx",
            }
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert schedule_service.reload_from_disk()
    assert schedule_service.resolve_group_canonical("25сж01") == "25СЖ01"
    assert schedule_service.get_doc_url("25СЖ01") == "https://example.com/f.docx"
    assert schedule_service.group_has_schedule_file("25СЖ01")


def test_group_hierarchy_helpers() -> None:
    path = config.SCHEDULES_PATH
    path.write_text(
        json.dumps(
            {
                "groups": {
                    "24СЖ02": {},
                    "25СЖ02": {},
                    "25СЖ01": {},
                    "25ПГС01": {},
                    "ABCD": {},
                }
            }
        ),
        encoding="utf-8",
    )
    schedule_service.reload_from_disk()
    assert schedule_service.split_group_name("25СЖ01") == ("25", "СЖ", "01")
    assert schedule_service.split_group_name("ABCD") is None
    assert schedule_service.get_group_years() == ["25", "24"]
    assert schedule_service.get_prefixes_for_year("25") == ["ПГС", "СЖ"]
    assert schedule_service.get_groups_for_year_prefix("25", "СЖ") == ["25СЖ01", "25СЖ02"]


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


def test_pe_subject_strips_inline_teachers() -> None:
    subj = (
        "Элективные курсы по физической культуре и спорту (Практические) СК «Тезуче» "
        "доц. Калманович В.Л., доц. Архипов Е.Ю."
    )
    line = schedule_service.format_lesson_line_html(
        {"time": "9:40-11:10", "subject": subj, "room": "", "teacher": ""}
    )
    assert "Калманович" not in line
    assert "Архипов" not in line
    assert "Тезуче" in line
    assert "физической культуре" in line


def test_non_pe_subject_keeps_inline_teachers() -> None:
    subj = "Математический анализ доц. Иванов И.И."
    line = schedule_service.format_lesson_line_html(
        {"time": "10:00-11:30", "subject": subj, "room": "", "teacher": ""}
    )
    assert "Иванов" in line


def test_physical_chemistry_not_treated_as_pe() -> None:
    subj = "Физическая химия доц. Петров П.П."
    assert schedule_service.display_subject(subj) == subj


def test_lessons_for_calendar_week_filters_by_parity() -> None:
    lessons = [
        {"time": "1", "subject": "Even only", "week_parity": "even"},
        {"time": "2", "subject": "Odd only", "week_parity": "odd"},
        {"time": "3", "subject": "Always", "teacher": ""},
    ]
    d_w1 = date(2024, 1, 3)  # ISO week 1 (odd) → inverted → «чётная» / Чет rows
    assert schedule_service.calendar_week_parity_for_date(d_w1) == "even"
    got = schedule_service._lessons_for_calendar_week(lessons, d_w1)
    assert [x["subject"] for x in got] == ["Even only", "Always"]
    d_w2 = date(2024, 1, 8)  # ISO week 2 (even) → «нечётная» / Неч rows
    assert schedule_service.calendar_week_parity_for_date(d_w2) == "odd"
    got_e = schedule_service._lessons_for_calendar_week(lessons, d_w2)
    assert [x["subject"] for x in got_e] == ["Odd only", "Always"]


def test_split_telegram_chunks() -> None:
    assert schedule_service.split_telegram_chunks("") == []
    short = "hello"
    assert schedule_service.split_telegram_chunks(short) == ["hello"]
    big = "x" * 100
    parts = schedule_service.split_telegram_chunks(big, limit=30)
    assert len(parts) > 1
    assert "".join(parts).replace("\n", "") == big


def test_build_week_txt_has_separators_and_spacing() -> None:
    full = {d: [] for d in schedule_service.WEEKDAYS}
    full["Monday"] = [
        {"time": "9:40-11:10", "subject": "Математика"},
        {"time": "11:20-12:50", "subject": "Физика"},
    ]
    txt = schedule_service._build_week_txt(full, date(2024, 1, 8))
    assert "Понедельник\n\n9:40-11:10 - Математика\n\n11:20-12:50 - Физика" in txt
    assert "--------------------" in txt


def test_teachers_blob_one_two_three() -> None:
    assert (
        schedule_service.format_teachers_blob_display("доц. Иванов И.И.")
        == "доц. Иванов И.И."
    )
    two = "доц. Иванов И.И., доц. Петров П.П."
    assert schedule_service.format_teachers_blob_display(two) == two
    three = "доц. А А., доц. Б Б., преп. В В."
    assert schedule_service.format_teachers_blob_display(three) == "доц. А А., доц. Б Б. и др."


def test_format_lesson_html_splits_course_and_teachers() -> None:
    line = schedule_service.format_lesson_line_html(
        {
            "time": "8:00-9:30",
            "subject": "Химия (Лабораторные) доц. Сидоров С.С.",
            "room": "",
            "teacher": "",
        }
    )
    assert "Химия (Лабораторные)" in line
    assert "Сидоров" in line
    assert "доц." in line


def test_week_txt_includes_indented_teachers() -> None:
    full = {d: [] for d in schedule_service.WEEKDAYS}
    full["Wednesday"] = [
        {
            "time": "8:00-9:30",
            "subject": "Химия (Лабораторные) доц. Иванов И.И.",
        },
    ]
    txt = schedule_service._build_week_txt(full, date(2024, 1, 8))
    assert "8:00-9:30 - Химия (Лабораторные)" in txt
    assert "    доц. Иванов И.И." in txt
