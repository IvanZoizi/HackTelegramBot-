from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from data import db_session

from token import token  # Токен бота

bot = Bot(token)
dp = Dispatcher(bot, storage=MemoryStorage())


@dp.message_handler(commands='start')  # Примерно
async def start(message: types.Message):
    await message.answer("Старт")


if __name__ == '__main__':
    db_session.global_init('db/user.db')
    executor.start_polling(dp, skip_updates=True)
