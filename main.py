from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from secrets import token_hex

from classes import Token, Join, ORDER, Dodo

from token_get import token, user, password, db_name, host, port, api_org  # Токен бота
import psycopg2
import requests
import asyncio

import pandas as pd

bot = Bot(token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


@dp.message_handler(commands='start')  # Примерно
async def start(message: types.Message):
    await message.answer(
        "Привет. Для начала создай токен, чтобы пользователи могли короче подключаться, с помощью команды /create_token.\n"
        "Если уже есть рума подключись используйте команду /join_team")


@dp.message_handler(commands='create_token', state='*')
async def create_token_start(message: types.Message):
    await message.answer("Введите пароль комнаты")
    await Token.start.set()


@dp.message_handler(state=Token.start)
async def create_token_password(message: types.Message, state: FSMContext):
    try:
        token = token_hex(16)
        with open('tokens.txt', 'r') as file:
            text = file.readlines()
        with open('tokens.txt', 'w') as file:
            text.append(f"{token} \t {message.text}")
            file.write('\n'.join(text))
        cur = con.cursor()
        cur.execute("""INSERT INTO userinfo (name, id_chat) VALUES (%s, %s)""", (message.from_user.username,
                                                                                 str(message.chat.id)))
        con.commit()
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
            cur.execute("""INSERT INTO userinfo (name, id_chat) VALUES (%s, %s)""", (message.from_user.username,
                                                                                     str(message.chat.id)))
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


@dp.message_handler(commands=['собрать_заказ'])
async def order(message: types.Message, state: FSMContext):
    cur.execute("""SELECT * FROM userinfo WHERE name = %s""", (message.from_user.username,))
    user = cur.fetchone()
    if user:
        # Получение ресторанов
        texts = ['ресторан Дода пицца Дубна', 'ресторан Дубна']
        response = []
        for text in texts:
            res = requests.get(
                f'https://search-maps.yandex.ru/v1/?text={text}&type=geo&lang=ru_RU&apikey={api_org}&type=biz').json()
            response.append(res)
        n = []
        buttons = []
        for res in response:
            for name in res['features'][1:]:
                try:
                    names = name['properties']['CompanyMetaData']['name']
                    phone = name['properties']['CompanyMetaData']['Phones'][0]['formatted']
                    url = name['properties']['CompanyMetaData']['url']
                    n.append(f"Название - {names}. Номер телефона - {phone}. Ссылка на сайт - {url}")
                    buttons.append(names)
                except Exception:
                    pass
        button_restoranov = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
            *[KeyboardButton(i) for i in buttons])
        await state.update_data(user_name=user[1], chat_id=user[2])
        await message.answer('Для заказа следуйте дальнейшей инструкцией.')
        await message.answer('Выберете ресторан', reply_markup=button_restoranov)
        await message.answer('\n'.join([f"{id + 1}) {i}" for id, i in enumerate(n)]))
        await ORDER.RESTORAN.set()
    else:
        await message.answer("Вы не подключены к компании")
        await state.finish()


@dp.message_handler(state=ORDER.RESTORAN)
async def rest_step(message: types.Message, state: FSMContext):
    response = []
    for text in ['ресторан Дода пицца Дубна', 'ресторан Дубна']:
        response.append(requests.get(
            f'https://search-maps.yandex.ru/v1/?text={text}&type=geo&lang=ru_RU&apikey={api_org}&type=biz').json())
    buttons = []
    for res in response:
        for name in res['features'][1:]:
            try:
                names = name['properties']['CompanyMetaData']['name']
                url = name['properties']['CompanyMetaData']['url']
                buttons.append(names)
            except Exception:
                pass
    if message.text.lower() not in list(map(str.lower, buttons)):
        task = asyncio.create_task(order(message, state))
        await task
    else:
        await state.update_data(RESTORAN=message.text)
        await message.answer('Напишите реквизиты для сбора денег')  # два варианта: контакт, номер карты.
        await ORDER.PAY_INFO.set()


@dp.message_handler(state=ORDER.PAY_INFO)
async def pay_info_step(message: types.Message, state: FSMContext):
    await state.update_data(PAY_INFO=message.text)
    await message.answer('Напишите ограничение по времени. Например: 5 мин')
    await ORDER.TIME.set()


@dp.message_handler(state=ORDER.TIME)
async def time_step(message: types.Message, state: FSMContext):
    # проверка коррект времени
    await state.update_data(TIME=message.text)
    await message.answer('Если у вас есть промокод на скидку напишите.')
    await ORDER.PROMO.set()


@dp.message_handler(state=ORDER.PROMO)
async def promo_step(message: types.Message, state: FSMContext):
    cur.execute("SELECT (id_chat) FROM userinfo")
    names = cur.fetchall()
    await state.update_data(PROMO=message.text)
    data = await state.get_data()
    buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
        *[KeyboardButton(i) for i in ['Да', 'Нет']])
    for id in names:
        # if id != message.chat.id:
        await bot.send_message(id[0], f"Заказ. Рестаран - {data['RESTORAN']}. Время - {data['TIME']}."
                                      f"Принять заказ?", reply_markup=buttons)
    # рассылка сообщений await mybot.bot.send_message(627976213, текст о далн инструк)
    await message.answer('Ожидайте заказа сотрудников')
    cur.execute("""SELECT (id) FROM userinfo WHERE name = %s""", (message.from_user.username,))
    user = cur.fetchone()
    cur.execute("""INSERT INTO order_user (user_id) VALUES (%s)""", (user,))
    con.commit()
    await ORDER.WAIT.set()


@dp.message_handler(state=ORDER.WAIT)
async def wait_step(message: types.Message, state: FSMContext):
    if message.text.capitalize() == 'Да':
        task = asyncio.create_task(accept_order(message, state))
        await task
    elif message.text.capitalize() == 'Нет':
        await state.finish()
        await message.answer("Спасибо за ваше мнение")
    else:
        buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
            *[KeyboardButton(i) for i in ['Да', 'Нет']])
        await message.answer("Попробуйте еще раз", reply_markup=buttons)
    # Для аналитики
    csv = pd.read_csv("analiz.csv")
    df = pd.concat([csv, pd.DataFrame({'name': message.from_user.username, 'answer': message.text}, index=[0])], axis=0,
                   ignore_index=True)
    df = df[['name', 'answer']]
    df.to_csv("analiz.csv")


async def accept_order(message: types.Message, state: FSMContext):
    # Для каждого ресторана, прописана своя функция. Перевел в числа названия
    data = await state.get_data()
    if data['RESTORAN'].lower() == 'додо пицца':
        await message.answer("Вы выбрали Додо Пицца. Давайте посмотрим меню")
        task = asyncio.create_task(pizza(message, state))
        await task


@dp.message_handler(state=Dodo.back)
async def pizza(message: types.Message, state: FSMContext):
    if message.text.capitalize() not in ['Оплатить', 'Добавить', 'Да']:
        await message.answer("Попробуйте еще раз")
    elif message.text.capitalize() == 'Оплатить':
        buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
            *[KeyboardButton(i) for i in ['Телеграмм', 'Сам']])
        await message.answer("Переходим к оплате. Хотите отплатить переводом через Телеграмм или своим путем?",
                                reply_markup=buttons)
        await Dodo.result.set()
    else:
        # Вывожу меню
        header = {'CountryCode': '643', 'LanguageCode': 'ru', 'ApiVersion': '1', 'User-Agent': 'PostmanRuntime/7.29.0',
                  'Accept': '*/*', 'Accept-Encoding': 'gzip, deflate', 'Connection': 'keep-alive'}
        ans = requests.get('https://mapi.dodopizza.ru/api/v4/menu/restaurant/643/00000140-0000-0000-0000-000000000000',
                           headers=header).json()
        dic_categori = {"1": 'Пицца', '6': "Десерт", '3': 'Закуски', '2': "Напитки"}
        categories = sorted(list(set([dic_categori[str(name['category'])] for name in ans['items'] if str(name['category']) in dic_categori.keys()])))
        # Получаю категории, пример, пицца, десерт
        buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
            *[KeyboardButton(i) for i in categories])
        await message.answer('\n'.join([f"{id + 1}) {i}" for id, i in enumerate(categories)]), reply_markup=buttons)
        await message.answer("Какую категорию вы хотите выбрать?")
        await Dodo.menu.set()


@dp.message_handler(state=Dodo.menu)
async def pizza_menu(message: types.Message, state: FSMContext):
    dic_cat = {"Пицца": 1, 'Десерт': 6, 'Закуски': 3, 'Напитки': 2}
    # Проверка на корректность ввода
    if message.text.lower() not in list(map(str.lower, dic_cat.keys())):
        await message.answer("Попробуйте еше раз")
        await state.finish()
        task = asyncio.create_task(pizza(message, state))
        await task
    header = {'CountryCode': '643', 'LanguageCode': 'ru', 'ApiVersion': '1', 'User-Agent': 'PostmanRuntime/7.29.0',
              'Accept': '*/*', 'Accept-Encoding': 'gzip, deflate', 'Connection': 'keep-alive'}
    ans = requests.get('https://mapi.dodopizza.ru/api/v4/menu/restaurant/643/00000140-0000-0000-0000-000000000000',
                       headers=header).json()
    cat = dic_cat[message.text.capitalize()]
    food = [f"{name['name']} - {'-'.join(sorted(list(set([str(name['shoppingItems'][i]['price']) for i in range(len(name['shoppingItems']))]))))}"
            for name in ans['items'] if name['category'] == cat]
    food.insert(0, "Название. Цена")
    await state.update_data(categorial=cat, menu=food[1:])
    await message.answer('\n'.join(food))
    await Dodo.add.set()
    await message.answer("Напишите название и количество блюд, которые выхотите заказать.\n"
                         "Пример. Манго-шейк/2, Айс Капучино/1")


@dp.message_handler(state=Dodo.add)
async def add_menu(message: types.Message, state: FSMContext):
    # Обработка меню
    data = await state.get_data()
    menu = data['menu']
    foods = {}
    for food_price in menu:
        foods[food_price.split(' - ')[0].capitalize()] = float(food_price.split(' - ')[1])
    # Проверка
    message_user = message.text.split(',')
    if not all([food.lstrip().rstrip().split('/')[0].capitalize() in list(foods) for food in message_user]):
        await message.answer("Неверный формат ввода")
    else:
        food = [food.lstrip().rstrip().split('/')[0].capitalize() for food in message_user]
        price = 0
        for order in message_user:
            price += float(order.split('/')[1]) * foods[order.split('/')[0].capitalize()]
        if 'price' in data.keys():
            price += data['price']
        if 'food' in data.keys():
            food += data['food']
        buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
                *[KeyboardButton(i) for i in ['Оплатить', 'Добавить']])
        await state.update_data(price=price, food=food)
        await message.answer("Еще добавим блюда или оформим заказ?", reply_markup=buttons)
        await Dodo.back.set()


"""@dp.message_handler(state=Dodo.back)
async def pizza_back(message: types.Message, state: FSMContext):
    if message.text.capitalize() not in ['Оплатить', 'Добавить']:
        await message.answer("Попробуйте еще раз")
    else:
        if message.text.capitalize() == 'Оплатить':
            buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
                *[KeyboardButton(i) for i in ['Телеграмм', 'Сам']])
            await message.answer("Переходим к оплате. Хотите отплатить переводом через Телеграмм или своим путем?",
                                 reply_markup=buttons)
            await Dodo.result.set()
        else:
            await message.answer("Посмотрим еще раз меню")
            await Dodo.menu.set()"""


@dp.message_handler(state=Dodo.result)
async def pizza_result(message: types.Message, state: FSMContext):
    if message.text.capitalize() not in ['Телеграмм', 'Сам']:
        await message.answer("Попробуйте еще раз")
    else:
        if message.text.capitalize() == 'Сам':
            data = await state.get_data()
            print(data['food'])
            user_name, chat_id = data['user_name'], data['chat_id']
            await message.answer(f"Заказ оформлен. Пользователь {user_name} ждет отплаты")
            await bot.send_message(chat_id, f"Заказ оформил {message.from_user.username}, на сумму {data['price']}.\n"
                                            f"Сам заказ - {','.join(data['food'])}")
        else:
            pass
            # Допили пж)))


if __name__ == '__main__':
    con = psycopg2.connect(f"dbname={db_name} host={host} password={password} port={port} user={user}")
    cur = con.cursor()
    executor.start_polling(dp, skip_updates=True)
