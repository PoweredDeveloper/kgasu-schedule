import math
import re
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery
from zoneinfo import ZoneInfo

import bot.texts as T
import config
from bot.keyboards.inline import (
    group_pagination,
    home_kb,
    manual_cancel_kb,
    onboarding_kb,
    service_kb,
)
from bot.services import schedule_service
from bot.services import user_prefs
from bot.services.schedule_service import WEEKDAYS, format_lesson_line_html
from bot.services.user_state import Flow
from bot.utils.fetch import download_bytes

router = Router()


def _safe_filename(name: str) -> str:
    s = re.sub(r"[^\w\d\u0400-\u04FF\-.]+", "_", name, flags=re.UNICODE).strip("_")
    return (s or "schedule")[:72]


async def _edit(query: CallbackQuery, text: str, kb, *, parse_mode: str = "HTML") -> None:
    try:
        await query.message.edit_text(text, reply_markup=kb, parse_mode=parse_mode)
    except TelegramBadRequest:
        pass


def _pick_pages(total: int) -> int:
    return max(1, math.ceil(total / config.GROUPS_PAGE_SIZE) if total else 1)


@router.callback_query(F.data == "k:bon")
async def cb_back_onboard(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.set_state(Flow.onboarding)
    await _edit(query, T.onboarding_html(), onboarding_kb())


@router.callback_query(F.data == "k:tin")
async def cb_type_manual(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.set_state(Flow.enter_manual)
    await _edit(query, T.manual_prompt_html(), manual_cancel_kb())


@router.callback_query(F.data == "k:sl")
async def cb_select_list(query: CallbackQuery, state: FSMContext) -> None:
    groups = schedule_service.get_all_groups()
    if not groups:
        await query.answer(T.GROUP_LIST_EMPTY, show_alert=True)
        return
    await query.answer()
    await state.set_state(Flow.picking_group)
    await state.update_data(page=0)
    pages = _pick_pages(len(groups))
    await _edit(
        query,
        T.pick_page_html(0, pages),
        group_pagination(groups, 0),
    )


@router.callback_query(F.data.startswith("k:pg:"))
async def cb_page(query: CallbackQuery, state: FSMContext) -> None:
    groups = schedule_service.get_all_groups()
    if not groups:
        await query.answer(T.GROUP_LIST_EMPTY, show_alert=True)
        return
    try:
        page = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        await query.answer()
        return
    await query.answer()
    await state.update_data(page=page)
    pages = _pick_pages(len(groups))
    await _edit(
        query,
        T.pick_page_html(page, pages),
        group_pagination(groups, page),
    )


@router.callback_query(F.data.startswith("k:i:"))
async def cb_pick(query: CallbackQuery, state: FSMContext) -> None:
    groups = schedule_service.get_all_groups()
    try:
        idx = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        await query.answer(T.UNKNOWN_GROUP, show_alert=True)
        return
    if idx < 0 or idx >= len(groups):
        await query.answer(T.UNKNOWN_GROUP, show_alert=True)
        return
    name = groups[idx]
    await query.answer()
    user_prefs.set_group(query.from_user.id, name)
    await state.set_state(Flow.home)
    await state.update_data(group=name)
    has = schedule_service.count_lessons(name) > 0
    await _edit(
        query,
        T.home_html(name, has),
        home_kb(has_lessons=has),
    )


@router.callback_query(F.data == "k:cg")
async def cb_change_group(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    user_prefs.clear_group(query.from_user.id)
    await state.clear()
    await state.set_state(Flow.onboarding)
    await _edit(query, T.onboarding_html(), onboarding_kb())


@router.callback_query(F.data == "k:smn")
async def cb_service_menu(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await _edit(query, T.service_menu_html(), service_kb())


@router.callback_query(F.data == "k:bhm")
async def cb_back_home(query: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    group = data.get("group")
    if not group:
        await query.answer(T.UNKNOWN_GROUP, show_alert=True)
        return
    await query.answer()
    has = schedule_service.count_lessons(group) > 0
    await _edit(
        query,
        T.home_html(group, has),
        home_kb(has_lessons=has),
    )


@router.callback_query(F.data == "k:hp")
async def cb_help(query: CallbackQuery) -> None:
    await query.answer()
    await query.message.answer(T.help_html(), parse_mode="HTML")


@router.callback_query(F.data == "k:rl")
async def cb_reload(query: CallbackQuery) -> None:
    ok = schedule_service.reload_from_disk()
    await query.answer(T.RELOAD_OK if ok else T.RELOAD_FAIL, show_alert=not ok)


@router.callback_query(F.data == "k:fl")
async def cb_full_file(query: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    group = data.get("group")
    if not group:
        await query.answer(T.UNKNOWN_GROUP, show_alert=True)
        return
    await query.answer()
    has = schedule_service.count_lessons(group) > 0
    if has:
        body = schedule_service.build_full_schedule_txt(group)
        fn = f"raspisanie_{_safe_filename(group)}.txt"
        await query.message.answer_document(
            BufferedInputFile(body.encode("utf-8"), filename=fn),
            caption="<b>Вот целиком</b> <i>(.txt из кэша)</i>",
            parse_mode="HTML",
        )
    else:
        url = schedule_service.get_doc_url(group)
        if not url:
            await query.message.answer(
                "<i>Нет ни распарсенных пар, ни ссылки на файл — пингани админа.</i>",
                parse_mode="HTML",
            )
        else:
            try:
                raw = await download_bytes(url)
            except Exception:
                await query.message.answer(
                    "<i>Не смог скачать .doc с сайта — открой вручную:</i>\n" + url,
                    parse_mode="HTML",
                )
            else:
                fn = url.rsplit("/", 1)[-1].split("?")[0] or "raspisanie.doc"
                if not fn.lower().endswith(".doc"):
                    fn += ".doc"
                await query.message.answer_document(
                    BufferedInputFile(raw, filename=fn[:120]),
                    caption="<b>Официальный файл</b> с сайта <i>(парсер тут пустой)</i>",
                    parse_mode="HTML",
                )
    await query.message.answer(
        "<i>Что дальше?</i>",
        parse_mode="HTML",
        reply_markup=home_kb(has_lessons=has),
    )


@router.callback_query(F.data == "k:td")
async def cb_today(query: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    group = data.get("group")
    if not group:
        await query.answer(T.UNKNOWN_GROUP, show_alert=True)
        return
    await query.answer()
    lessons = schedule_service.get_today(group)
    z = ZoneInfo(config.TZ)
    wd = datetime.now(z).weekday()
    title = T.DAY_LABEL_RU.get(WEEKDAYS[wd], "")
    if not lessons:
        body = f"<b>{title}</b>\n\n{T.NO_LESSONS_HTML}"
    else:
        lines = [f"<b>{title}</b>", ""] + [format_lesson_line_html(x) for x in lessons]
        body = "\n".join(lines)
    await query.message.answer(body, parse_mode="HTML")
    has = schedule_service.count_lessons(group) > 0
    await query.message.answer(
        "<i>Назад к кнопкам 👇</i>",
        parse_mode="HTML",
        reply_markup=home_kb(has_lessons=has),
    )


@router.callback_query(F.data == "k:tmr")
async def cb_tomorrow(query: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    group = data.get("group")
    if not group:
        await query.answer(T.UNKNOWN_GROUP, show_alert=True)
        return
    await query.answer()
    lessons = schedule_service.get_tomorrow(group)
    z = ZoneInfo(config.TZ)
    t = (datetime.now(z).date() + timedelta(days=1)).weekday()
    title = T.DAY_LABEL_RU.get(WEEKDAYS[t], "")
    if not lessons:
        body = f"<b>{title}</b>\n\n{T.NO_LESSONS_HTML}"
    else:
        lines = [f"<b>{title}</b>", ""] + [format_lesson_line_html(x) for x in lessons]
        body = "\n".join(lines)
    await query.message.answer(body, parse_mode="HTML")
    has = schedule_service.count_lessons(group) > 0
    await query.message.answer(
        "<i>Назад к кнопкам 👇</i>",
        parse_mode="HTML",
        reply_markup=home_kb(has_lessons=has),
    )
