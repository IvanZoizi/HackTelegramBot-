from aiogram.dispatcher.filters.state import State, StatesGroup


class Token(StatesGroup):
    start = State()
    city = State()