"""Russian copy for students (HTML where the bot uses parse_mode=HTML)."""

from __future__ import annotations

from datetime import datetime, timedelta
from html import escape
from zoneinfo import ZoneInfo

import config


def week_bits_html() -> str:
    """«Чётная»/«нечётная» in TZ - inverted vs ISO week # so it matches KGASU tables (see schedule_service)."""
    z = ZoneInfo(config.TZ)
    now = datetime.now(z)
    _, iso_week, iso_wday = now.isocalendar()
    monday = now.date() - timedelta(days=iso_wday - 1)
    sunday = monday + timedelta(days=6)
    span = f"{monday.strftime('%d.%m')}–{sunday.strftime('%d.%m')}"
    if iso_week % 2 == 0:
        kind = "нечётная"
    else:
        kind = "чётная"
    return (
        f"<b>{span}</b> - по календарю это <b>{kind}</b> неделя "
    )


def onboarding_html() -> str:
    return (
        "Привет! 👋\n\n"
        "Я подтягиваю расписание с сайта КГАСУ.\n"
        "Как удобнее указать свою группу?"
    )


def home_html(group: str, *, has_schedule_file: bool) -> str:
    g = escape(group)
    w = week_bits_html()
    if has_schedule_file:
        body = (
            f"Ты в <b>{g}</b>.\n"
            f"{w}\n\n"
            "<i>Первая кнопка открывает официальный файл на сайте. «Сегодня» / «Завтра» / «Вся неделя» — бот скачивает файл и разбирает его в момент нажатия.</i>\n"
            "<i>Если что-то не так — открой файл по первой кнопке.</i>"
        )
    else:
        body = (
            f"Ты в <b>{g}</b>.\n"
            f"{w}\n\n"
            "<i>Для группы нет ссылки на файл - пусть админ прогонит scraper.</i>\n"
        )
    return body


def service_menu_html() -> str:
    return (
        "<b>Менюшка</b>\n"
        "<i>😎</i>"
    )


def support_html() -> str:
    c = (config.SUPPORT_CONTACT or "").strip()
    if c:
        return f"<b>Поддержка</b>\n{escape(c)}"
    return "<b>Поддержка</b>\n<i>Свяжись с администратором бота.</i>"


def help_html() -> str:
    return (
        "<b>Коротко</b>\n"
        "• <b>Список</b> - листаешь группы кнопками.\n"
        "• Можно <b>просто написать группу в чат</b> - и со старта, и пока листаешь список.\n"
        "• Кнопка <b>«Ввести вручную»</b> - то же, только с подсказкой. "
        "<i>Регистр не важен</i>, латинская <code>C</code> = русская <code>С</code>.\n"
        "• Бот <b>запоминает</b> группу. <b>Сменить группу</b> - выбрать заново.\n"
        "• <b>Обновить кэш</b> - только перечитать файл на сервере; "
        "если данных нет, пингани того, кто крутит <code>scraper</code>.\n"
        "• <b>Всё расписание (файл)</b> — ссылка на официальный Word на сайте КГАСУ.\n"
        "• <b>Сегодня</b> / <b>Завтра</b> / <b>Вся неделя</b> — бот скачивает файл и разбирает его "
        "<b>в момент нажатия</b> (в кэше только список групп и ссылка на файл).\n"
        "• Учитывается <b>чётная / нечётная неделя</b> по календарю (как «Чет»/«Неч» в таблице).\n\n"
    )


def pick_page_html(page: int, total_pages: int) -> str:
    return (
        f"<b>Листай и жми свою группу</b> <i>(стр. {page + 1} из {total_pages})</i>\n\n"
        "<i>Лень листать? Просто <b>напиши название группы</b> отдельным сообщением в чат - "
        "пойму и так.</i>\n"
        "<i>Кнопка «Ввести вручную» - то же самое, только с подсказкой.</i>"
    )


def pick_year_html(total_years: int) -> str:
    return (
        f"<b>Шаг 1 из 3: выбери год</b> <i>({total_years} вариантов)</i>\n\n"
        "<i>Или напиши полное название группы вручную.</i>"
    )


def pick_prefix_html(year: str, total_prefixes: int) -> str:
    return (
        f"<b>Шаг 2 из 3: выбери поток</b> <i>({year} год, {total_prefixes} вариантов)</i>\n\n"
        "<i>Например: СЖ, ПГС и т.д.</i>"
    )


def pick_group_html(year: str, prefix: str, total_groups: int) -> str:
    return (
        f"<b>Шаг 3 из 3: выбери группу</b> <i>({year} {prefix}, {total_groups} вариантов)</i>\n\n"
        "<i>После выбора сразу откроются кнопки расписания.</i>"
    )


def manual_prompt_html() -> str:
    return (
        "Напиши <b>название группы</b> одним сообщением - как на сайте.\n"
        "<i>Можно капсом/строчными, лишние пробелы уберу.</i>"
    )


def manual_not_found_html(suggestions: list[str]) -> str:
    lines = [
        "<b>Такой группы нет в моём кэше</b> 🤔",
        "",
        "Часто это значит, что <b>скрапер ещё не подтянул</b> свежие файлы с сайта "
        "(например, набор <b>25…</b> появился, а в кэше пока только <b>24…</b>). "
        # "Попроси админа: Docker-профиль <code>scheduler</code> или разовый запуск "
        # "<code>docker compose --profile manual run --rm scraper</code>.",
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

GROUP_LIST_EMPTY = "В кэше пусто - сначала нужен scraper."

UNKNOWN_GROUP = "Сначала выбери группу."

NO_LESSONS_HTML = "<i>Пар не нашлось - отдыхай (или глянь файл).</i>"

SCHEDULE_ERR_NO_DOC = "<i>Нет ссылки на файл расписания - пусть админ прогонит scraper.</i>"
SCHEDULE_ERR_DOWNLOAD = "<i>Не удалось скачать файл с сайта. Попробуй позже или открой официальный файл.</i>"
SCHEDULE_ERR_EXTRACT = "<i>Не вышло извлечь текст из файла (пусто или битый файл).</i>"

BTN_FROM_LIST = "Из списка"
BTN_TYPE_MANUAL = "Ввести вручную"
BTN_FULL_FILE = "Всё расписание (файл)"
BTN_WHOLE_WEEK = "Вся неделя"
BTN_TODAY = "Сегодня"
BTN_TOMORROW = "Завтра"
BTN_MENU = "Меню"
BTN_CHANGE_GROUP = "Сменить группу"
BTN_TO_SCHEDULE = "К расписанию"
BTN_SUPPORT = "Поддержка"
BTN_HELP = "Помощь"
BTN_RELOAD = "Обновить кэш"
BTN_BACK_HOME = "К расписанию"
BTN_NEXT = "Далее"
BTN_PREV = "Назад"
BTN_BACK = "Назад"

RELOAD_OK = "Готово, перечитал файл."
RELOAD_FAIL = "Файл не читается - админу смотреть логи."

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
