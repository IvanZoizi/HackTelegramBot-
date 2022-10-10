from aiogram.dispatcher.filters.state import State, StatesGroup


class Join(StatesGroup):
    start = State()


class ORDER(StatesGroup):
    RESTORAN = State()
    PAY_INFO = State()
    TIME = State()
    PROMO = State()
    WAIT = State()


class Dodo(StatesGroup):
    menu = State()
    add = State()
    price = State()
    back = State()
    result = State()


class Fank(StatesGroup):
    menu = State()
    add = State()
    price = State()
    back = State()
    result = State()


class Limonad(StatesGroup):
    menu = State()
    add = State()
    back = State()
    price = State()
    result = State()


class Iberia(StatesGroup):
    menu = State()
    add = State()
    price = State()
    back = State()
    result = State()