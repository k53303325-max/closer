from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    pep = State()
    contact = State()


class ProfileStates(StatesGroup):
    filling = State()
