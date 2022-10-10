from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ContentType

from secrets import token_hex

from classes import Join, ORDER, Dodo, Fank, Limonad, Iberia

from token_get import token, user, password, db_name, host, port, api_org, token_pay  # Токен бота
import psycopg2
import requests
import asyncio
import aioschedule
import pandas as pd

bot = Bot(token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


@dp.message_handler(commands='start', state='*')
async def start(message: types.Message, state: FSMContext):
    await message.answer(
        "Привет👋. Я бот для автоматизации сбора заказов в вашем офисе.\n"
        "Для начало работы, создайте токен для приглашения в компанию с помощью команды /create_token.\n"
        "Если вам скинули токен для приглашения, то присоединитесь к компнаии с помощью команды /join_team\nЕсли вы заблудитесь, используйте команду /help")
    await state.finish()


@dp.message_handler(commands='create_token', state='*')
async def create_token_start(message: types.Message):
    try:
        token = token_hex(16)
        with open('tokens.txt', 'r') as file:
            text = file.readlines()
        with open('tokens.txt', 'w') as file:
            text.append(f"{token}")
            file.write('\n'.join(text))
        cur = con.cursor()
        cur.execute("""INSERT INTO userinfo (name, id_chat) VALUES (%s, %s)""", (message.from_user.username,
                                                                                 str(message.chat.id)))
        con.commit()
        await message.answer(f"Вы успешно создали компанию")
        await message.answer(f'{token}')
    except Exception:
        await message.answer("Возможно, вы уже создали компанию")


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
            await message.answer("Вы успешно присоединились к компании")
        else:
            await message.answer("Такого токена не существует. Попробуйте еще раз")
        await state.finish()
    except Exception as e:
        await message.answer("Возможно вы уже присоединились к компании")
        await state.finish()


@dp.message_handler(commands=['заказ'])
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
                    if 'Дубна' in names or 'Камелот' in names:
                        continue
                    phone = name['properties']['CompanyMetaData']['Phones'][0]['formatted']
                    url = name['properties']['CompanyMetaData']['url']
                    n.append(f"Название - {names}.\nНомер телефона - {phone}.\nСсылка на сайт - {url}")
                    buttons.append(names)
                except Exception:
                    pass
        button_restoranov = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
            *[KeyboardButton(i) for i in buttons])
        await state.update_data(user_name=user[1], chat_id=user[2])
        await message.answer('Для заказа следуйте дальнейшей инструкцией')
        await message.answer('Выберите ресторан', reply_markup=button_restoranov)
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
                if 'Дубна' in names or 'Камелот' in names:
                    continue
                url = name['properties']['CompanyMetaData']['url']
                buttons.append(names)
            except Exception:
                pass
    if message.text.lower() not in list(map(str.lower, buttons)):
        task = asyncio.create_task(order(message, state))
        await task
    else:
        await state.update_data(RESTORAN=message.text)
        await message.answer('Укажите реквизиты для оплаты заказа коллегами 💳')  # два варианта: контакт, номер карты.
        await ORDER.PAY_INFO.set()


@dp.message_handler(state=ORDER.PAY_INFO)
async def pay_info_step(message: types.Message, state: FSMContext):
    try:
        int(message.text)
        await state.update_data(PAY_INFO=message.text)
        buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
            *[KeyboardButton(i) for i in ['10 минут', '30 минут', '1 час', '1 час 30 минут', '3 часа']])
        await message.answer('Выберите ограничения ожидания заказа по времени', reply_markup=buttons)
        await ORDER.TIME.set()
    except ValueError:
        await message.answer("Попробуйте еще раз")
        await message.answer('Укажите реквизиты для оплаты заказа коллегами 💳')


@dp.message_handler(state=ORDER.TIME)
async def time_step(message: types.Message, state: FSMContext):
    if message.text.lower() not in ['10 минут', '30 минут', '1 час', '1 час 30 минут', '3 часа']:
        await message.answer("Попробуйте еще раз")
        buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
            *[KeyboardButton(i) for i in ['10 миинут', '30 минут', '1 час', '1 час 30 минут', '3 часа']])
        await message.answer('Выберите ограничения ожидания заказа по времени', reply_markup=buttons)
    else:
        dic = {'10 минут': 5, '30 минут': 30 * 60, '1 час': 3600, '1 час 30 минут': 3600 + 30 * 60, '3 часа': 3 * 3600}
        await state.update_data(TIME=message.text)
        cur.execute("SELECT (id_chat) FROM userinfo")
        names = cur.fetchall()
        data = await state.get_data()
        await message.answer('Ожидайте заказа сотрудников')
        buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
            *[KeyboardButton(i) for i in ['Да', 'Нет']])
        cur.execute("""SELECT (id) FROM userinfo WHERE name = %s""", (message.from_user.username,))
        user = cur.fetchone()
        cur.execute("""INSERT INTO order_user (user_id) VALUES (%s)""", (user,))
        con.commit()
        cur.execute("""SELECT (id) FROM order_user WHERE user_id = %s""", (user,))
        order = cur.fetchone()
        # """        await state.update_data(order=order)"""
        for id in names:
            await bot.send_message(id[0], f"Заказ. Ресторан - {data['RESTORAN']}. Время - {data['TIME']}."
                                          f"Принять заказ?", reply_markup=buttons)
            state_user = dp.current_state(chat=int(id[0]), user=int(id[0]))
            await state_user.set_state(ORDER.WAIT)
            await state_user.update_data(RESTORAN=data['RESTORAN'], TIME=data['TIME'],
                                         PAY_INFO=data['PAY_INFO'], user_name=data['user_name'],
                                         chat_id=data['chat_id'], order=order)
        # добавление заказа в БД
        loop.create_task(
            scheduled(dic[message.text.lower()], user_name=data['user_name'], chat_id=data['chat_id'], order=order,
                      id=user))
        await ORDER.WAIT.set()


@dp.message_handler(state=ORDER.WAIT)
async def wait_step(message: types.Message, state: FSMContext):
    # принимает пользователь заказ или нет
    if message.text.capitalize() == 'Да':
        task = asyncio.create_task(accept_order(message, state))
        await task
    elif message.text.capitalize() == 'Нет':
        await state.finish()
        await message.answer("Спасибо за ответ")
    else:
        buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
            *[KeyboardButton(i) for i in ['Да', 'Нет']])
        await message.answer("Попробуйте еще раз", reply_markup=buttons)


async def accept_order(message: types.Message, state: FSMContext):
    # Для каждого ресторана, прописана своя функция. Перевел в числа названия
    data = await state.get_data()
    if data['RESTORAN'].lower() == 'додо пицца':
        await message.answer("Вы выбрали ресторан Додо Пицца 🍕\n Давайте посмотрим меню")
        task = asyncio.create_task(pizza(message, state))
        await task
    elif data['RESTORAN'].lower() == 'фанки':
        await message.answer("Вы выбрали ресторан Фанки 🍲\nДавайте посмотрим меню")
        task = asyncio.create_task(fank(message, state))
        await task
    elif data['RESTORAN'].lower() == 'лимонад':
        await message.answer("Вы выбрали ресторан Лимонад 🥤\nДавайте посмотрим меню")
        task = asyncio.create_task(limonad(message, state))
        await task
    elif data['RESTORAN'].lower() == 'иберия':
        await message.answer("Вы выбрали ресторан Иберия 🥗\nДавайте посмотрим меню")
        task = asyncio.create_task(iberia(message, state))
        await task
    else:
        await message.answer("Попробуйте еще раз")


@dp.message_handler(state=Dodo.back)
async def pizza(message: types.Message, state: FSMContext):
    # Проверка на корректность ввода
    if message.text.capitalize() not in ['Оплатить', 'Добавить', 'Да', 'Назад']:
        await message.answer("Попробуйте еще раз")
    # оплата
    elif message.text.capitalize() == 'Оплатить':
        buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
            *[KeyboardButton(i) for i in ['Телеграмм', 'Получить реквизиты']])
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
        categories = sorted(list(set([dic_categori[str(name['category'])] for name in ans['items'] if
                                      str(name['category']) in dic_categori.keys()])))
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
    header = {'CountryCode': '643', 'LanguageCode': 'ru', 'ApiVersion': '1', 'User-Agent': 'PostmanRuntime/7.29.0',
              'Accept': '*/*', 'Accept-Encoding': 'gzip, deflate', 'Connection': 'keep-alive'}
    ans = requests.get('https://mapi.dodopizza.ru/api/v4/menu/restaurant/643/00000140-0000-0000-0000-000000000000',
                       headers=header).json()
    cat = dic_cat[message.text.capitalize()]
    # Создания меню
    if cat != 1:
        food = []
        food_name = []
        for name in ans['items']:
            if name['category'] == cat and name['name'] not in food_name:
                food.append(
                    f"{name['name']} - {'-'.join(sorted(list(set([str(name['shoppingItems'][i]['price']) for i in range(len(name['shoppingItems']))]))))}")
                food_name.append(name['name'])
    else:
        food = [
            f"{name['name']} - {sorted(list(set([str(name['shoppingItems'][i]['price']) for i in range(len(name['shoppingItems']))])))[0] if len(sorted(list(set([str(name['shoppingItems'][i]['price']) for i in range(len(name['shoppingItems']))])))) == 1 else sorted(list(set([str(name['shoppingItems'][i]['price']) for i in range(len(name['shoppingItems']))])))[1]}"
            for name in ans['items'] if name['category'] == cat]
    food.insert(0, "Название. Цена")
    await state.update_data(categorial=cat, menu=food[1:])
    await message.answer('\n'.join(food))
    await Dodo.add.set()
    buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(KeyboardButton('Назад'))
    await message.answer("Введите названия блюд через запятую\n"
                         "Например: Манго-шейк", reply_markup=buttons)


@dp.message_handler(state=Dodo.add)
async def add_menu(message: types.Message, state: FSMContext):
    if message.text.lower() == 'назад':
        await message.answer("Возвращаемся назад")
        task = asyncio.create_task(pizza(message, state))
        await task
    # Обработка меню
    data = await state.get_data()
    menu = data['menu']
    foods = {}
    for food_price in menu:
        foods[food_price.split(' - ')[0].capitalize().strip()] = float(food_price.split(' - ')[1])
    # Проверка
    await state.update_data(foods=foods)
    food = [name.strip().capitalize() for name in message.text.split(',')]
    if not all([name in foods.keys() for name in food]):
        await message.answer("Неверный формат ввода")
    else:
        # Подведения чека
        await state.update_data(current_food=food)
        if 'food' in data.keys():
            food += data['food']
        await state.update_data(food=food)
        await message.answer("Введите количество блюд через запятую")
        await Dodo.price.set()


@dp.message_handler(state=Dodo.price)
async def pizza_price(message: types.Message, state: FSMContext):
    try:
        col = [int(name.strip()) for name in message.text.split(',')]
        if any([name > 20 for name in col]):
            await message.answer("Слишком большое количество блюд. Максимальное количество - 20")
            await message.answer("Введите количество")
        else:
            data = await state.get_data()
            foods = data['foods']
            current_food = data['current_food']
            if len(current_food) != len(col):
                await message.answer("Неправильный ввод. Попробуйте еще раз")
            else:
                price = 0
                check = []
                for i in range(len(col)):
                    price += int(foods[current_food[i]]) * col[i]
                    check.append(f"{current_food[i]}/{col[i]}")
                if 'price' in data.keys():
                    price += data['price']
                await state.update_data(price=price, food=check)
                buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
                    *[KeyboardButton(i) for i in ['Оплатить', 'Добавить']])
                await message.answer("Готово. Вы хотите оплатить или добавить блюда?", reply_markup=buttons)
                await Dodo.back.set()
    except ValueError:
        await message.answer("Попробуйте еще раз")
        await message.answer("Введите количество")


@dp.message_handler(state=Dodo.result)
async def pizza_result(message: types.Message, state: FSMContext):
    if message.text.capitalize() not in ['Телеграмм', 'Получить реквизиты']:
        await message.answer("Попробуйте еще раз")
    else:
        data = await state.get_data()
        if message.text.capitalize() == 'Получить реквизиты':
            user_name, chat_id = data['user_name'], data['chat_id']
            await message.answer(f"Заказ оформлен. Пользователь {user_name} ждет отплат\n"
                                 f"Заказ на сумму {data['price']}. Сам заказ - {','.join(data['food'])}")
            await bot.send_message(chat_id, f"Заказ оформил {message.from_user.username}, на сумму {data['price']}.\n"
                                            f"Сам заказ - {','.join(data['food'])}")
            csv = pd.read_csv("order.csv")
            dic = {'name': message.from_user.username, 'order': ','.join(data['food']), 'price': data['price'],
                   'restoran': data['RESTORAN']}
            csv = pd.concat([csv, pd.DataFrame(dic, index=[0])], ignore_index=True, axis=0)
            csv = csv[['name', 'order', 'price', 'restoran']]
            csv.to_csv('order.csv')
            cur.execute("""SELECT id FROM userinfo WHERE name = %s""", (user_name,))
            user = cur.fetchone()
            cur.execute("""INSERT INTO orderrespose (id_order, id_user, price, order_text) VALUES (%s, %s, %s, %s)""",
                        (data['order'], user, data['price'], data['food']))
            con.commit()
            await state.finish()
        elif message.text.capitalize() == 'Телеграмм':
            PRICE = types.LabeledPrice(label=f"{data['RESTORAN']}",
                                       amount=int(data['price'] * 100))

            await bot.send_invoice(message.chat.id,
                                   title=f"{data['RESTORAN']}",
                                   description=f"Заказ: {','.join(data['food'])}",
                                   provider_token=token_pay,
                                   currency="rub",
                                   is_flexible=False,
                                   prices=[PRICE],
                                   start_parameter='pay-order',
                                   payload="test-invoice-payload")
            await state.finish()
            user_name = data['user_name']
            cur.execute("""SELECT id FROM userinfo WHERE name = %s""", (user_name,))
            user = cur.fetchone()
            cur.execute("""INSERT INTO orderrespose (id_order, id_user, price, order_text) VALUES (%s, %s, %s, %s)""",
                        (data['order'], user, data['price'], data['food']))
            con.commit()


# pre checkout  (must be answered in 10 seconds)
@dp.pre_checkout_query_handler(lambda query: True)
async def pre_checkout_query(pre_checkout_q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


# successful payment
@dp.message_handler(content_types=ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: types.Message):
    print("SUCCESSFUL PAYMENT:")
    payment_info = message.successful_payment.to_python()
    for k, v in payment_info.items():
        print(f"{k} = {v}")

    await bot.send_message(message.chat.id,
                           f"Платеж на сумму {message.successful_payment.total_amount // 100} {message.successful_payment.currency} прошел успешно!!!")


"""Остальные функции индентичны. Разница в считке данных и их выводе
Есть 4 рестарана Додо, Лимонад, Фанка и Иберия"""


@dp.message_handler(state=Fank.back)
async def fank(message: types.Message, state: FSMContext):
    if message.text.capitalize() not in ['Оплатить', 'Добавить', 'Да']:
        await message.answer("Попробуйте еще раз")
    elif message.text.capitalize() == 'Оплатить':
        buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
            *[KeyboardButton(i) for i in ['Телеграмм', 'Получить реквизиты']])
        await message.answer("Оплата. Выберите способ оплаты: Телеграмм, Получить реквизиты инициатора заказа",
                             reply_markup=buttons)
        await Fank.result.set()
    else:
        with open('fak.txt', 'r', encoding='utf-8') as file:
            text = ''.join(file.readlines()).split('\n')
        await state.update_data(menu=text)
        buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
            *[KeyboardButton(i) for i in ['Завтрак', 'Пицца', 'Салаты']])
        await message.answer('\n'.join([f"{id + 1}) {i}" for id, i in enumerate(['Завтрак', 'Пицца', 'Салаты'])]),
                             reply_markup=buttons)
        await message.answer("Выберите категорию", reply_markup=buttons)
        await Fank.menu.set()


@dp.message_handler(state=Fank.result)
async def fank_result(message: types.Message, state: FSMContext):
    if message.text.capitalize() not in ['Телеграмм', 'Получить реквизиты']:
        await message.answer("Попробуйте еще раз")
    else:
        if message.text.capitalize() == 'Получить реквизиты':
            data = await state.get_data()
            user_name, chat_id = data['user_name'], data['chat_id']
            await message.answer(f"Заказ оформлен. Пользователь {user_name} ждет отплаты")
            await bot.send_message(chat_id, f"Заказ оформил {message.from_user.username}, на сумму {data['price']}.\n"
                                            f"Сам заказ - {','.join(data['food'])}")
            csv = pd.read_csv("order.csv")
            dic = {'name': message.from_user.username, 'order': ','.join(data['food']), 'price': data['price'],
                   'restoran': data['RESTORAN']}
            csv = pd.concat([csv, pd.DataFrame(dic, index=[0])], ignore_index=True, axis=0)
            csv = csv[['name', 'order', 'price', 'restoran']]
            csv.to_csv('order.csv')
            cur.execute("""SELECT id FROM userinfo WHERE name = %s""", (user_name,))
            user = cur.fetchone()
            cur.execute("""INSERT INTO orderrespose (id_order, id_user, price, order_text) VALUES (%s, %s, %s, %s)""",
                        (data['order'], user, data['price'], data['food']))
            con.commit()
        elif message.text.capitalize() == 'Телеграмм':
            data = await state.get_data()
            PRICE = types.LabeledPrice(label=f"{data['RESTORAN']}",
                                       amount=int(data['price'] * 100))

            await bot.send_invoice(message.chat.id,
                                   title=f"{data['RESTORAN']}",
                                   description=f"Заказ: {','.join(data['food'])}",
                                   provider_token=token_pay,
                                   currency="rub",
                                   is_flexible=False,
                                   prices=[PRICE],
                                   start_parameter='pay-order',
                                   payload="test-invoice-payload")
            user_name = data['user_name']
            cur.execute("""SELECT id FROM userinfo WHERE name = %s""", (user_name,))
            user = cur.fetchone()
            cur.execute("""INSERT INTO orderrespose (id_order, id_user, price, order_text) VALUES (%s, %s, %s, %s)""",
                        (data['order'], user, data['price'], data['food']))
            con.commit()


@dp.message_handler(state=Fank.menu)
async def fank_menu(message: types.Message, state: FSMContext):
    dic_cat = {"Пицца": '2', 'Завтрак': '1', 'Салаты': '3'}
    # Проверка на корректность ввода
    if message.text.lower() not in list(map(str.lower, dic_cat.keys())):
        await message.answer("Попробуйте еше раз")
    else:
        cat = dic_cat[message.text.capitalize()]
        data = await state.get_data()
        menu = data['menu']
        food = [f"{i.split('-')[1]} - {i.split('-')[-1]}" for i in menu if i.split('-')[0] == cat]
        food.insert(0, 'Название. Цена')
        await state.update_data(categorial=cat, menu=food[1:])
        await message.answer('\n'.join(food))
        await Fank.add.set()
        buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(KeyboardButton('Назад'))
        await message.answer("Напишите название блюд, которые выхотите заказать.\n"
                             "Пример. Манго-шейк", reply_markup=buttons)


@dp.message_handler(state=Fank.add)
async def fank_add(message: types.Message, state: FSMContext):
    if message.text.lower() == 'назад':
        await message.answer("Возвращаемся назад")
        task = asyncio.create_task(fank(message, state))
        await task
    # Обработка меню
    data = await state.get_data()
    menu = data['menu']
    foods = {}
    for food_price in menu:
        foods[food_price.split(' - ')[0].capitalize().strip()] = float(food_price.split(' - ')[1])
    # Проверка
    await state.update_data(foods=foods)
    food = [name.strip().capitalize() for name in message.text.split(',')]
    if not all([name in foods.keys() for name in food]):
        await message.answer("Неверный формат ввода")
    else:
        # Подведения чека
        await state.update_data(current_food=food)
        if 'food' in data.keys():
            food += data['food']
        await state.update_data(food=food)
        await message.answer("Введите количество блюд через запятую")
        await Fank.price.set()


@dp.message_handler(state=Fank.price)
async def fank_price(message: types.Message, state: FSMContext):
    try:
        col = [int(name.strip()) for name in message.text.split(',')]
        if any([name > 20 for name in col]):
            await message.answer("Слишком большое количество блюд. Максимальное количество - 20")
            await message.answer("Введите количество")
        else:
            data = await state.get_data()
            foods = data['foods']
            current_food = data['current_food']
            if len(current_food) != len(col):
                await message.answer("Неправильный ввод. Попробуйте еще раз")
            else:
                price = 0
                check = []
                for i in range(len(col)):
                    price += int(foods[current_food[i]]) * col[i]
                    check.append(f"{current_food[i]}/{col[i]}")
                if 'price' in data.keys():
                    price += data['price']
                await state.update_data(price=price, food=check)
                buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
                    *[KeyboardButton(i) for i in ['Оплатить', 'Добавить']])
                await message.answer("Готово. Вы хотите оплатить или добавить блюда?", reply_markup=buttons)
                await Fank.back.set()
    except ValueError:
        await message.answer("Попробуйте еще раз")
        await message.answer("Введите количество")


@dp.message_handler(state=Limonad.back)
async def limonad(message: types.Message, state: FSMContext):
    if message.text.capitalize() not in ['Оплатить', 'Добавить', 'Да', 'Назад']:
        await message.answer("Попробуйте еще раз")
    elif message.text.capitalize() == 'Оплатить':
        buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
            *[KeyboardButton(i) for i in ['Телеграмм', 'Получить реквизиты']])
        await message.answer("Оплата. Выберите способ оплаты: Телеграмм, Получить реквизиты инициатора заказа",
                             reply_markup=buttons)
        await Limonad.result.set()
    else:
        with open('limonad.txt', 'r', encoding='utf-8') as file:
            text = ''.join(file.readlines()).split('\n')
        await state.update_data(menu=text)
        buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
            *[KeyboardButton(i) for i in ['Супы', 'Стейки', 'Десерты', 'Паста']])
        await message.answer(
            '\n'.join([f"{id + 1}) {i}" for id, i in enumerate(['Супы', 'Стейки', 'Десерты', 'Паста'])]),
            reply_markup=buttons)
        await message.answer("Выберите категорию", reply_markup=buttons)
        await Limonad.menu.set()


@dp.message_handler(state=Limonad.result)
async def limonad_result(message: types.Message, state: FSMContext):
    if message.text.capitalize() not in ['Телеграмм', 'Получить реквизиты']:
        await message.answer("Попробуйте еще раз")
    else:
        if message.text.capitalize() == 'Получить реквизиты':
            data = await state.get_data()
            user_name, chat_id = data['user_name'], data['chat_id']
            await message.answer(f"Заказ оформлен. Пользователь {user_name} ждет отплаты")
            await bot.send_message(chat_id, f"Заказ оформил {message.from_user.username}, на сумму {data['price']}.\n"
                                            f"Сам заказ - {','.join(data['food'])}")
            csv = pd.read_csv("order.csv")
            dic = {'name': message.from_user.username, 'order': ','.join(data['food']), 'price': data['price'],
                   'restoran': data['RESTORAN']}
            csv = pd.concat([csv, pd.DataFrame(dic, index=[0])], ignore_index=True, axis=0)
            csv = csv[['name', 'order', 'price', 'restoran']]
            csv.to_csv('order.csv')
            cur.execute("""SELECT id FROM userinfo WHERE name = %s""", (user_name,))
            user = cur.fetchone()
            cur.execute("""INSERT INTO orderrespose (id_order, id_user, price, order_text) VALUES (%s, %s, %s, %s)""",
                        (data['order'], user, data['price'], data['food']))
            con.commit()
        elif message.text.capitalize() == 'Телеграмм':
            data = await state.get_data()
            PRICE = types.LabeledPrice(label=f"{data['RESTORAN']}",
                                       amount=int(data['price'] * 100))

            await bot.send_invoice(message.chat.id,
                                   title=f"{data['RESTORAN']}",
                                   description=f"Заказ: {','.join(data['food'])}",
                                   provider_token=token_pay,
                                   currency="rub",
                                   is_flexible=False,
                                   prices=[PRICE],
                                   start_parameter='pay-order',
                                   payload="test-invoice-payload")
            user_name = data['user_name']
            cur.execute("""SELECT id FROM userinfo WHERE name = %s""", (user_name,))
            user = cur.fetchone()
            cur.execute("""INSERT INTO orderrespose (id_order, id_user, price, order_text) VALUES (%s, %s, %s, %s)""",
                        (data['order'], user, data['price'], data['food']))
            con.commit()


@dp.message_handler(state=Limonad.menu)
async def limonad_menu(message: types.Message, state: FSMContext):
    dic_cat = {"Паста": '2', 'Супы': '1', 'Десерты': '3', 'Стейки': '4'}
    # Проверка на корректность ввода
    if message.text.lower() not in list(map(str.lower, dic_cat.keys())):
        await message.answer("Попробуйте еше раз")
    else:
        cat = dic_cat[message.text.capitalize()]
        data = await state.get_data()
        menu = data['menu']
        food = [f"{i.split('-')[1]} - {i.split('-')[-1]}" for i in menu if i.split('-')[0] == cat]
        food.insert(0, 'Название. Цена')
        await state.update_data(categorial=cat, menu=food[1:])
        await message.answer('\n'.join(food))
        await Limonad.add.set()
        buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(KeyboardButton('Назад'))
        await message.answer("Напишите название блюд, которые выхотите заказать.\n"
                             "Пример. Манго-шейк", reply_markup=buttons)


@dp.message_handler(state=Limonad.add)
async def limonad_add(message: types.Message, state: FSMContext):
    if message.text.lower() == 'назад':
        await message.answer("Возвращаемся назад")
        task = asyncio.create_task(limonad(message, state))
        await task
    # Обработка меню
    data = await state.get_data()
    menu = data['menu']
    foods = {}
    for food_price in menu:
        foods[food_price.split(' - ')[0].capitalize().strip()] = float(food_price.split(' - ')[1])
    # Проверка
    await state.update_data(foods=foods)
    food = [name.strip().capitalize() for name in message.text.split(',')]
    if not all([name in foods.keys() for name in food]):
        await message.answer("Неверный формат ввода")
    else:
        # Подведения чека
        await state.update_data(current_food=food)
        if 'food' in data.keys():
            food += data['food']
        await state.update_data(food=food)
        await message.answer("Введите количество блюд через запятую")
        await Limonad.price.set()


@dp.message_handler(state=Limonad.price)
async def limonad_price(message: types.Message, state: FSMContext):
    try:
        col = [int(name.strip()) for name in message.text.split(',')]
        if any([name > 20 for name in col]):
            await message.answer("Слишком большое количество блюд. Максимальное количество - 20")
            await message.answer("Введите количество")
        else:
            data = await state.get_data()
            foods = data['foods']
            current_food = data['current_food']
            if len(current_food) != len(col):
                await message.answer("Неправильный ввод. Попробуйте еще раз")
            else:
                price = 0
                check = []
                for i in range(len(col)):
                    price += int(foods[current_food[i]]) * col[i]
                    check.append(f"{current_food[i]}/{col[i]}")
                if 'price' in data.keys():
                    price += data['price']
                await state.update_data(price=price, food=check)
                buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
                    *[KeyboardButton(i) for i in ['Оплатить', 'Добавить']])
                await message.answer("Готово. Вы хотите оплатить или добавить блюда?", reply_markup=buttons)
                await Limonad.back.set()
    except ValueError:
        await message.answer("Попробуйте еще раз")
        await message.answer("Введите количество")


@dp.message_handler(state=Iberia.back)
async def iberia(message: types.Message, state: FSMContext):
    if message.text.capitalize() not in ['Оплатить', 'Добавить', 'Да', "Назад"]:
        await message.answer("Попробуйте еще раз")
    elif message.text.capitalize() == 'Оплатить':
        buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
            *[KeyboardButton(i) for i in ['Телеграмм', 'Получить реквизиты']])
        await message.answer("Оплата. Выберите способ оплаты: Телеграмм, Получить реквизиты инициатора заказа",
                             reply_markup=buttons)
        await Iberia.result.set()
    else:
        with open('iberia.txt', 'r', encoding='utf-8') as file:
            text = ''.join(file.readlines()).split('\n')
        await state.update_data(menu=text)
        buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
            *[KeyboardButton(i) for i in ['Шашлык', 'Блюда на заказ', 'Горячие блюда', 'Блюда из рыбы']])
        await message.answer('\n'.join(
            [f"{id + 1}) {i}" for id, i in enumerate(['Шашлык', 'Блюда на заказ', 'Горячие блюда', 'Блюда из рыбы'])]),
            reply_markup=buttons)
        await message.answer("Выберите категорию", reply_markup=buttons)
        await Iberia.menu.set()


@dp.message_handler(state=Iberia.result)
async def iberia_result(message: types.Message, state: FSMContext):
    if message.text.capitalize() not in ['Телеграмм', 'Получить реквизиты']:
        await message.answer("Попробуйте еще раз")
    else:
        if message.text.capitalize() == 'Получить реквизиты':
            data = await state.get_data()
            user_name, chat_id = data['user_name'], data['chat_id']
            await message.answer(f"Заказ оформлен. Пользователь {user_name} ждет отплаты")
            await bot.send_message(chat_id, f"Заказ оформил {message.from_user.username}, на сумму {data['price']}.\n"
                                            f"Сам заказ - {','.join(data['food'])}")
            # Аналитика
            csv = pd.read_csv("order.csv")
            dic = {'name': message.from_user.username, 'order': ','.join(data['food']), 'price': data['price'],
                   'restoran': data['RESTORAN']}
            csv = pd.concat([csv, pd.DataFrame(dic, index=[0])], ignore_index=True, axis=0)
            csv = csv[['name', 'order', 'price', 'restoran']]
            csv.to_csv('order.csv')
            cur.execute("""SELECT id FROM userinfo WHERE name = %s""", (user_name,))
            user = cur.fetchone()
            cur.execute("""INSERT INTO orderrespose (id_order, id_user, price, order_text) VALUES (%s, %s, %s, %s)""",
                        (data['order'], user, data['price'], data['food']))
            con.commit()
        elif message.text.capitalize() == 'Телеграмм':
            data = await state.get_data()
            PRICE = types.LabeledPrice(label=f"{data['RESTORAN']}",
                                       amount=int(data['price'] * 100))

            await bot.send_invoice(message.chat.id,
                                   title=f"{data['RESTORAN']}",
                                   description=f"Заказ: {','.join(data['food'])}",
                                   provider_token=token_pay,
                                   currency="rub",
                                   is_flexible=False,
                                   prices=[PRICE],
                                   start_parameter='pay-order',
                                   payload="test-invoice-payload")
            user_name = data['user_name']
            cur.execute("""SELECT id FROM userinfo WHERE name = %s""", (user_name,))
            user = cur.fetchone()
            cur.execute("""INSERT INTO orderrespose (id_order, id_user, price, order_text) VALUES (%s, %s, %s, %s)""",
                        (data['order'], user, data['price'], data['food']))
            con.commit()


@dp.message_handler(state=Iberia.menu)
async def iberia_menu(message: types.Message, state: FSMContext):
    dic_cat = {"Шашлык": '1', 'Блюда на заказ': '2', 'Горячие блюда': '3', 'Блюда из рыбы': '4'}
    # Проверка на корректность ввода
    if message.text.lower() not in list(map(str.lower, dic_cat.keys())):
        await message.answer("Попробуйте еше раз")
    else:
        cat = dic_cat[message.text.capitalize()]
        data = await state.get_data()
        menu = data['menu']
        food = [f"{i.split('-')[1]} - {i.split('-')[-1]}" for i in menu if i.split('-')[0] == cat]
        food.insert(0, 'Название. Цена')
        await state.update_data(categorial=cat, menu=food[1:])
        await message.answer('\n'.join(food))
        await Iberia.add.set()
        buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(KeyboardButton('Назад'))
        await message.answer("Напишите название, которые выхотите заказать.\n"
                             "Пример. Манго-шейк", reply_markup=buttons)


@dp.message_handler(state=Iberia.add)
async def iberia_add(message: types.Message, state: FSMContext):
    if message.text.lower() == 'назад':
        await message.answer("Возвращаемся назад")
        task = asyncio.create_task(limonad(message, state))
        await task
    # Обработка меню
    data = await state.get_data()
    menu = data['menu']
    foods = {}
    for food_price in menu:
        foods[food_price.split(' - ')[0].capitalize().strip()] = float(food_price.split(' - ')[1])
    # Проверка
    await state.update_data(foods=foods)
    food = [name.strip().capitalize() for name in message.text.split(',')]
    if not all([name in foods.keys() for name in food]):
        await message.answer("Неверный формат ввода")
    else:
        # Подведения чека
        await state.update_data(current_food=food)
        if 'food' in data.keys():
            food += data['food']
        await state.update_data(food=food)
        await message.answer("Введите количество блюд через запятую")
        await Iberia.price.set()


@dp.message_handler(state=Iberia.price)
async def iberia_price(message: types.Message, state: FSMContext):
    try:
        col = [int(name.strip()) for name in message.text.split(',')]
        if any([name > 20 for name in col]):
            await message.answer("Слишком большое количество блюд. Максимальное количество - 20")
            await message.answer("Введите количество")
        else:
            data = await state.get_data()
            foods = data['foods']
            current_food = data['current_food']
            if len(current_food) != len(col):
                await message.answer("Неправильный ввод. Попробуйте еще раз")
            else:
                price = 0
                check = []
                for i in range(len(col)):
                    price += int(foods[current_food[i]]) * col[i]
                    check.append(f"{current_food[i]}/{col[i]}")
                if 'price' in data.keys():
                    price += data['price']
                await state.update_data(price=price, food=check)
                buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
                    *[KeyboardButton(i) for i in ['Оплатить', 'Добавить']])
                await message.answer("Готово. Вы хотите оплатить или добавить блюда?", reply_markup=buttons)
                await Iberia.back.set()
    except ValueError:
        await message.answer("Попробуйте еще раз")
        await message.answer("Введите количество")


async def scheduled(wait_for, id, user_name, chat_id, order):
    await asyncio.sleep(wait_for)
    print(user_name, chat_id, order)
    cur.execute("""SELECT orderrespose.price, orderrespose.order_text, orderrespose.id_user, userinfo.name FROM orderrespose 
INNER JOIN userinfo ON userinfo.id = orderrespose.id_user WHERE orderrespose.id_order = %s""", (order,))
    answer = cur.fetchall()
    if len(answer) > 0:
        print(answer)
        new_answer_message = ['Время вышло. Чек:']
        for id, info in enumerate(answer):
            new_answer_message.append(F"Заказ номер {id + 1} от {info[-1]} на сумму {info[0]}. Заказ {info[1][1:-1]}")
        await bot.send_message(chat_id, '\n'.join(new_answer_message))
    else:
        await bot.send_message(chat_id, 'Заказ никто не принял')
    cur.execute("""SELECT id_chat FROM userinfo""")
    users = cur.fetchall()
    for chat_id in users:
        state_user = dp.current_state(chat=int(chat_id[0]), user=int(chat_id[0]))
        await bot.send_message(chat_id[0], f"Заказ пользователя {user_name} закончился")
        await state_user.finish()
    cur.execute("""DELETE FROM orderrespose WHERE id_order = %s""", (order,))
    con.commit()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    con = psycopg2.connect(f"dbname={db_name} host={host} password={password} port={port} user={user}")
    cur = con.cursor()
    executor.start_polling(dp, skip_updates=True)
