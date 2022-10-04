from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from secrets import token_hex

from classes import Token

from token_get import token  # Токен бота

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
    token = token_hex(16)
    with open('tokens.txt', 'r') as file:
        text = file.readlines()
    print(text)
    with open('tokens.txt', 'w') as file:
        text.append(f'{token}-{message.text}')
        file.write('\n'.join(text))
    await message.answer(f"Вы успешно создали комнату. Токен - {token}")
    await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
