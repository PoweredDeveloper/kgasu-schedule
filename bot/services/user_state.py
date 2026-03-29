from aiogram.fsm.state import State, StatesGroup


class Flow(StatesGroup):
    onboarding = State()
    picking_group = State()
    enter_manual = State()
    home = State()
