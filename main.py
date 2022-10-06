from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from secrets import token_hex

from classes import Token, Join

from token_get import token, user, password, db_name, host, port  # Токен бота
import psycopg2

bot = Bot(token)
dp = Dispatcher(bot, storage=MemoryStorage())


@dp.message_handler(commands='start')  # Примерно
async def start(message: types.Message):
    await message.answer("Привет. Для начала создай токен, чтобы пользователи могли короче подключаться, с помощью команды /create_token.\n"
                         "Если уже есть рума подключись используйте команду /join_team")


@dp.message_handler(commands='create_token', state='*')
async def create_token_start(message: types.Message):
    await message.answer("Введите пароль комнаты")
    await Token.start.set()


@dp.message_handler(state=Token.start)
async def create_token_password(message: types.Message, state: FSMContext):
    try:
        token = token_hex(16)
        print(1)
        with open('tokens.txt', 'r') as file:
            text = file.readlines()
        with open('tokens.txt', 'w') as file:
            file.write(f"{token} \t {message.text}")
        print(1)
        cur = con.cursor()
        cur.execute("""INSERT INTO userinfo (name) VALUES (%s)""", (message.from_user.username,))
        con.commit()
        print(1)
        await message.answer(f"Вы успешно создали комнату. Токен - {token}")
        await state.finish()
    except Exception:
        await message.answer("Возможно вы уже создавали комнату")
        await state.finish()


@dp.message_handler(commands='join_team', state='*')
async def join_token_start(message: types.Message, state: FSMContext):
    await message.answer("Введите токен")
    await Join.start.set()


@dp.message_handler(state=Join.start)
async def join_token_start(message: types.Message, state: FSMContext):
    try:
        with open("tokens.txt", 'r') as file:
            text = file.readlines()
        if any([lambda x: x in text, message.text]):
            print(1)
            cur.execute("""INSERT INTO userinfo (name) VALUES (%s)""", (message.from_user.username,))
            con.commit()
            await message.answer("Успешно")
        else:
            await message.answer("Такого токена не существует. Попробуйте еще раз")
        await state.finish()
    except Exception as e:
        await message.answer("Возможно вы уже присоединились к комнате")
        await state.finish()


@dp.message_handler(commands='quit_team')
async def quit_team(message: types.Message):
    cur.execute("""SELECT (name) FROM userinfo WHERE name = %s""", (message.from_user.username,))
    user = cur.fetchone()
    if user:
        cur.execute("""DELETE FROM userinfo WHERE name = %s""", (message.from_user.username,))
        con.commit()
        await message.answer('Вы вышли из комнаты')
    else:
        await message.answer("У вас нету комнат")


if __name__ == '__main__':
    con = psycopg2.connect(f"dbname={db_name} host={host} password={password} port={port} user={user}")
    cur = con.cursor()
    executor.start_polling(dp, skip_updates=True)
