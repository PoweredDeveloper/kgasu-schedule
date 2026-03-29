from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import bot.texts as T
from bot.keyboards.inline import home_kb, manual_cancel_kb, onboarding_kb, group_pagination
from bot.services import schedule_service
from bot.services import user_prefs
from bot.services.user_state import Flow
import config
import math

router = Router()


async def _send_home(message: Message, state: FSMContext, canon: str) -> None:
    user_prefs.set_group(message.from_user.id, canon)
    await state.set_state(Flow.home)
    await state.update_data(group=canon)
    has = schedule_service.count_lessons(canon) > 0
    await message.answer(
        T.home_html(canon, has),
        parse_mode="HTML",
        reply_markup=home_kb(has_lessons=has),
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
        page = int(data.get("page", 0))
        groups = schedule_service.get_all_groups()
        if groups:
            pages = max(1, math.ceil(len(groups) / config.GROUPS_PAGE_SIZE))
            await message.answer(
                T.pick_page_html(page, pages),
                parse_mode="HTML",
                reply_markup=group_pagination(groups, page),
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
