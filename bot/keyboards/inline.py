"""Inline keyboards (callback_data stays ASCII for Telegram limits)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import bot.texts as T
import config


def onboarding_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.BTN_FROM_LIST, callback_data="k:sl")
    b.button(text=T.BTN_TYPE_MANUAL, callback_data="k:tin")
    b.adjust(1)
    return b.as_markup()


def group_pagination(groups: list[str], page: int) -> InlineKeyboardMarkup:
    size = config.GROUPS_PAGE_SIZE
    n = len(groups)
    pages = max(1, (n + size - 1) // size)
    page = max(0, min(page, pages - 1))
    start = page * size
    chunk = groups[start : start + size]

    b = InlineKeyboardBuilder()
    for idx, name in enumerate(chunk):
        gidx = start + idx
        label = name if len(name) <= 48 else name[:45] + "…"
        b.button(text=label, callback_data=f"k:i:{gidx}")
    if page > 0:
        b.button(text=T.BTN_PREV, callback_data=f"k:pg:{page - 1}")
    if page < pages - 1:
        b.button(text=T.BTN_NEXT, callback_data=f"k:pg:{page + 1}")
    b.button(text=T.BTN_TYPE_MANUAL, callback_data="k:tin")
    b.button(text=T.BTN_BACK, callback_data="k:bon")
    b.adjust(1)
    return b.as_markup()


def home_kb(*, has_schedule_file: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.BTN_FULL_FILE, callback_data="k:fl")
    if has_schedule_file:
        b.button(text=T.BTN_TODAY, callback_data="k:td")
        b.button(text=T.BTN_TOMORROW, callback_data="k:tmr")
    b.button(text=T.BTN_MENU, callback_data="k:smn")
    b.button(text=T.BTN_CHANGE_GROUP, callback_data="k:cg")
    b.adjust(1)
    return b.as_markup()


def service_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.BTN_HELP, callback_data="k:hp")
    b.button(text=T.BTN_RELOAD, callback_data="k:rl")
    b.button(text=T.BTN_BACK_HOME, callback_data="k:bhm")
    b.adjust(1)
    return b.as_markup()


def manual_cancel_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.BTN_BACK, callback_data="k:bon")
    b.adjust(1)
    return b.as_markup()
