from aiogram.dispatcher.filters.state import State, StatesGroup


class Token(StatesGroup):
    start = State()


class Join(StatesGroup):
    start = State()