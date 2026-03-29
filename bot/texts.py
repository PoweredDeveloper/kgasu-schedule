"""Russian copy for students (HTML where the bot uses parse_mode=HTML)."""

from __future__ import annotations

from datetime import datetime, timedelta
from html import escape
from zoneinfo import ZoneInfo

import config


def week_bits_html() -> str:
    """Even/odd from the ISO week number in TZ (no site scrape — may differ from KGASU’s table by ±1)."""
    z = ZoneInfo(config.TZ)
    now = datetime.now(z)
    _, iso_week, iso_wday = now.isocalendar()
    monday = now.date() - timedelta(days=iso_wday - 1)
    sunday = monday + timedelta(days=6)
    span = f"{monday.strftime('%d.%m')}–{sunday.strftime('%d.%m')}"
    if iso_week % 2 != 0:
        kind = "чётная"
    else:
        kind = "нечётная"
    return (
        f"<b>{span}</b> — по календарю это <b>{kind}</b> неделя "
    )


def onboarding_html() -> str:
    return (
        "Привет! 👋\n\n"
        "Я подтягиваю расписание с сайта КГАСУ.\n"
        "Как удобнее указать свою группу?"
    )


def home_html(group: str, has_lessons: bool) -> str:
    g = escape(group)
    w = week_bits_html()
    if has_lessons:
        body = (
            f"Ты в <b>{g}</b>.\n"
            f"{w}\n\n"
            "<i>Ниже - быстрые кнопки.</i>"
        )
    else:
        body = (
            f"Ты в <b>{g}</b>.\n"
            f"{w}\n\n"
        )
    return body


def service_menu_html() -> str:
    return (
        "<b>Менюшка</b>\n"
        "<i>😎</i>"
    )


def help_html() -> str:
    return (
        "<b>Коротко</b>\n"
        "• <b>Список</b> — листаешь группы кнопками.\n"
        "• Можно <b>просто написать группу в чат</b> — и со старта, и пока листаешь список.\n"
        "• Кнопка <b>«Ввести вручную»</b> — то же, только с подсказкой. "
        "<i>Регистр не важен</i>, латинская <code>C</code> = русская <code>С</code>.\n"
        "• Бот <b>запоминает</b> группу. <b>Сменить группу</b> — выбрать заново.\n"
        "• <b>Обновить кэш</b> — только перечитать файл на сервере; "
        "если данных нет, пингани того, кто крутит <code>scraper</code>.\n\n"
    )


def pick_page_html(page: int, total_pages: int) -> str:
    return (
        f"<b>Листай и жми свою группу</b> <i>(стр. {page + 1} из {total_pages})</i>\n\n"
        "<i>Лень листать? Просто <b>напиши название группы</b> отдельным сообщением в чат — "
        "пойму и так.</i>\n"
        "<i>Кнопка «Ввести вручную» — то же самое, только с подсказкой.</i>"
    )


def manual_prompt_html() -> str:
    return (
        "Напиши <b>название группы</b> одним сообщением — как на сайте.\n"
        "<i>Можно капсом/строчными, лишние пробелы уберу.</i>"
    )


def manual_not_found_html(suggestions: list[str]) -> str:
    lines = [
        "<b>Такой группы нет в моём кэше</b> 🤔",
        "",
        "Часто это значит, что <b>скрапер ещё не подтянул</b> свежие файлы с сайта "
        "(например, набор <b>25…</b> появился, а в кэше пока только <b>24…</b>). "
        "Попроси админа: <code>docker compose --profile manual run --rm scraper</code>",
        "",
        "Проверь написание: латинская <code>C</code> = русская <code>С</code>, регистр не важен.",
    ]
    if suggestions:
        lines.append("")
        lines.append("<b>Похожие группы, которые уже есть в кэше:</b>")
        for g in suggestions:
            lines.append(f"• <code>{escape(g)}</code>")
    lines.append("")
    lines.append("<i>Можешь написать группу ещё раз или выбрать из списка кнопками.</i>")
    return "\n".join(lines)

GROUP_LIST_EMPTY = "В кэше пусто — сначала нужен scraper."

UNKNOWN_GROUP = "Сначала выбери группу."

NO_LESSONS_HTML = "<i>Пар не нашлось — отдыхай (или глянь файл).</i>"

BTN_FROM_LIST = "Из списка"
BTN_TYPE_MANUAL = "Ввести вручную"
BTN_FULL_FILE = "Всё расписание (файл)"
BTN_TODAY = "Сегодня"
BTN_TOMORROW = "Завтра"
BTN_MENU = "Меню"
BTN_CHANGE_GROUP = "Сменить группу"
BTN_HELP = "Помощь"
BTN_RELOAD = "Обновить кэш"
BTN_BACK_HOME = "К расписанию"
BTN_NEXT = "Далее"
BTN_PREV = "Назад"
BTN_BACK = "Назад"

RELOAD_OK = "Готово, перечитал файл."
RELOAD_FAIL = "Файл не читается — админу смотреть логи."

DAY_LABEL_RU = {
    "Monday": "Понедельник",
    "Tuesday": "Вторник",
    "Wednesday": "Среда",
    "Thursday": "Четверг",
    "Friday": "Пятница",
    "Saturday": "Суббота",
    "Sunday": "Воскресенье",
}

PART_HEADER = "<b>Часть {n} из {total}</b>\n\n"
