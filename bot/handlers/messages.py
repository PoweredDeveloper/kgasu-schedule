from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import bot.texts as T
from bot.keyboards.inline import (
    group_picker_kb,
    home_kb,
    manual_cancel_kb,
    onboarding_kb,
    prefix_picker_kb,
    year_picker_kb,
)
from bot.services import schedule_service
from bot.services import user_prefs
from bot.services.user_state import Flow

router = Router()


async def _send_home(message: Message, state: FSMContext, canon: str) -> None:
    user_prefs.set_group(message.from_user.id, canon)
    await state.set_state(Flow.home)
    await state.update_data(group=canon)
    has = schedule_service.group_has_schedule_file(canon)
    await message.answer(
        T.home_html(canon, has_schedule_file=has),
        parse_mode="HTML",
        reply_markup=home_kb(group=canon),
    )


@router.message(
    StateFilter(Flow.enter_manual, Flow.picking_group, Flow.onboarding),
    F.text,
)
async def text_as_group_name(message: Message, state: FSMContext) -> None:
    raw = message.text or ""
    if raw.startswith("/"):
        return

    canon = schedule_service.resolve_group_canonical(raw)
    if canon:
        await _send_home(message, state, canon)
        return

    sugg = schedule_service.suggest_groups(raw, limit=6)
    await message.answer(T.manual_not_found_html(sugg), parse_mode="HTML")

    st = await state.get_state()
    if st == Flow.picking_group.state:
        data = await state.get_data()
        stage = data.get("picker_stage")
        if stage == "group":
            year = data.get("picker_year")
            prefix = data.get("picker_prefix")
            groups = data.get("picker_groups") or []
            if year and prefix and groups:
                await message.answer(
                    T.pick_group_html(year, prefix, len(groups)),
                    parse_mode="HTML",
                    reply_markup=group_picker_kb(groups),
                )
                return
        if stage == "prefix":
            year = data.get("picker_year")
            prefixes = data.get("picker_prefixes") or []
            if year and prefixes:
                await message.answer(
                    T.pick_prefix_html(year, len(prefixes)),
                    parse_mode="HTML",
                    reply_markup=prefix_picker_kb(prefixes),
                )
                return
        years = data.get("picker_years") or schedule_service.get_group_years()
        if years:
            await message.answer(
                T.pick_year_html(len(years)),
                parse_mode="HTML",
                reply_markup=year_picker_kb(years),
            )
    elif st == Flow.enter_manual.state:
        await message.answer(
            T.manual_prompt_html(),
            parse_mode="HTML",
            reply_markup=manual_cancel_kb(),
        )
    elif st == Flow.onboarding.state:
        await message.answer(
            T.onboarding_html(),
            parse_mode="HTML",
            reply_markup=onboarding_kb(),
        )
