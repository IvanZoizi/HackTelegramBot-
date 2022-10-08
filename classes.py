from aiogram.dispatcher.filters.state import State, StatesGroup


class Token(StatesGroup):
    start = State()


class Join(StatesGroup):
    start = State()


class ORDER(StatesGroup):
    RESTORAN = State()
    PAY_INFO = State()
    TIME = State()
    PROMO = State()
    WAIT = State()