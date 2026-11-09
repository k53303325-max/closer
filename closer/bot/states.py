from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    pep = State()
    contact = State()


class ProfileStates(StatesGroup):
    filling = State()


class ComposeStates(StatesGroup):
    resume_choice = State()
    role = State()
    deal_text = State()
    ask_field = State()
    profile = State()
    card = State()
    edit_pick = State()
    edit_value = State()
    delete_confirm = State()
