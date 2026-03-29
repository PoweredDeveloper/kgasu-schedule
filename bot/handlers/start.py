from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import bot.texts as T
from bot.keyboards.inline import home_kb, onboarding_kb
from bot.services import schedule_service
from bot.services import user_prefs
from bot.services.user_state import Flow

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    schedule_service.reload_from_disk()
    uid = message.from_user.id
    saved = user_prefs.get_group(uid)
    canon = schedule_service.resolve_group_canonical(saved) if saved else None
    if saved and not canon:
        user_prefs.clear_group(uid)

    if canon:
        user_prefs.set_group(uid, canon)
        await state.set_state(Flow.home)
        await state.update_data(group=canon)
        has = schedule_service.group_has_schedule_file(canon)
        await message.answer(
            T.home_html(canon, has_schedule_file=has),
            parse_mode="HTML",
            reply_markup=home_kb(has_schedule_file=has),
        )
        return

    await state.set_state(Flow.onboarding)
    await message.answer(
        T.onboarding_html(),
        parse_mode="HTML",
        reply_markup=onboarding_kb(),
    )
