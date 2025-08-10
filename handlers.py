import logging
from difflib import get_close_matches

from aiogram import Router, types, F
from aiogram.filters import Command

from database import add_user, add_subscription, get_user_subscriptions, get_user, add_coin, get_coins, get_last_prices_for_subs_list, get_coin_from_list, get_coins_from_list, delete_user_subscription, update_user_subscription, get_user_subscriptions_settings, delete_coins
from coingecko import fetch_prices
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.enums.parse_mode import ParseMode
from aiogram.utils import markdown
from aiosqlite import Error as SQLError

logger = logging.getLogger(__name__)
router = Router()

available_tickers = {"BitCoin": "bitcoin", "DogeCoin": "dogecoin", "Ethereum": "ethereum", "Other": "other"}

class SubscribeState(StatesGroup):
    waiting_for_ticker = State()
    waiting_for_ticker_setting = State()

def get_main_menu() -> ReplyKeyboardMarkup:
    """
    Настраиваем кнопки главного меню бота
    :return: ReplyKeyboardMarkup
    """
    keyboard = [
        [KeyboardButton(text=f'Текущие цены')],
        [KeyboardButton(text=f'Мои подписки')],
        [KeyboardButton(text=f'Новая подписка')],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder=f'Выбери действие',
        is_persistent=True,
    )

def gen_ticker_kb() -> InlineKeyboardMarkup:
    """
    Настраиваем инлайн клавиатуру с тикерами коинов
    :return: InlineKeyboardMarkup
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=ticker, callback_data=f"sub:{slug}")]
            for ticker, slug in available_tickers.items()
        ]
    )

async def check_ticker_in_db(slug: str) -> bool:
    """
    Проверяет, есть ли уже такой тикер в БД
    :param slug: Имя тикера
    :return: bool
    """
    tickers = await get_coins()
    for ticker in tickers:
        if ticker[0] == slug:
            return True
    return False

async def check_subscription(user_id: int, slug: str) -> bool:
    """
    Проверяет, подписан ли юзер на этот тикер
    :param user_id: User ID
    :param slug: Тикер
    :return:
    """
    subs = await get_user_subscriptions(user_id)
    for user_id, coin, last_alert, alert_threshold, interval in subs:
        if coin == slug:
            return True
    return False

async def add_sub_to_db(user_id: int, slug: str) -> bool:
    """
    Добавляет подписку в БД
    :param user_id: id юзера
    :param slug: тикер
    :return: None
    """
    if not await check_ticker_in_db(slug):
        logger.debug(f'Ticker {slug} is not in DB')
        await add_coin(slug)
    if not await check_subscription(user_id, slug):
        logger.debug(f'User {user_id} is not subscribed to {slug}')
        await add_subscription(user_id, slug)
        return True
    return False

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Команда старт
    :param message: Сообщение
    :return:
    """
    try:
        user = await get_user(message.from_user.id)
        logger.debug(f'User is {user}')
        if not user:
            await add_user(message.from_user.id)
            await message.answer("Выберите криптовалюты для отслеживания:", reply_markup=gen_ticker_kb())
        else:
            await message.answer(f'Добро пожаловать! Выберите, что вы хотите сделать:', reply_markup=get_main_menu())
    except SQLError as error:
        logger.error(f'Error: {error}')

@router.callback_query(F.data.startswith("sub:"))
async def callback_subscribe(callback: types.CallbackQuery, state: FSMContext) -> None:
    """
    Добавляет новую подписку
    :param state:
    :param callback: Коллбек
    :return: None
    """
    slug = callback.data.split(":")[1]
    if slug == 'other': # проверяем ручной ввод
        await callback.message.answer(f'Введи название монеты:')
        await state.set_state(SubscribeState.waiting_for_ticker)
    else:
        if await add_sub_to_db(callback.from_user.id, slug):
            await fetch_prices([slug])
            logger.debug(f'User {callback.from_user.id} is not subscribed to {slug}')
            await callback.message.answer("Подписка добавлена!")
            await callback.message.answer(f"Вы подписались на {slug}")
        else:
            logger.debug(f'User {callback.from_user.id} was already subscribed to {slug}')
            await callback.message.answer(f'Вы уже были подписаны на {slug} ранее')
    await callback.message.answer(f'Добро пожаловать! Выберите, что вы хотите сделать:',
                                      reply_markup=get_main_menu())

@router.message(SubscribeState.waiting_for_ticker)
async def process_manual_ticker(message: types.Message, state: FSMContext):
    """
    Ручной ввод монеты (тикера)
    :param message: Монета
    :param state: Текущий стейт
    :return:
    """
    ticker = message.text.strip().lower()
    if not ticker.isalpha():
        await message.answer("Некорректный тикер. Попробуйте ещё раз.")
        return
    try:
        if not await get_coin_from_list(ticker):
            raise SQLError(f'Ticker not found')
        if await add_sub_to_db(message.from_user.id, ticker):
            await message.answer("Подписка добавлена!")
            await message.answer(f"Вы подписались на {ticker}")
        else:
            await message.answer(f'Вы уже были подписаны на {ticker} ранее')
        # await state.clear()
    except SQLError as error:
        coins = await get_coins_from_list()
        coins_list = []
        for coin in coins:
            coins_list.append(coin[0])
        similar = get_close_matches(message.text.strip().lower(), coins_list)
        await message.answer(f'Нет такой монеты')
        # await message.reply(f'Возможно имелось ввиду {similar[0]}?')
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=s, callback_data=f"sub:{s}")]
                for s in similar
            ]
        )
        await message.reply(f'Возможно имелось ввиду:', reply_markup=kb)
    finally:
        await state.clear()
        # await state.set_state(SubscribeState.waiting_for_ticker)

@router.message(F.text=='Мои подписки')
async def handle_my_subs(message: types.Message) -> None:
    """
    Отдаёт все подписки юзера
    :param message: Сообщение
    :return: Ответное сообщение
    """
    logger.debug(f'Try to get subs')
    subs = await get_user_subscriptions(message.from_user.id)
    logger.debug(f'User\'s subs: {subs}')
    answer = ''
    answer += f'Твои подписки:\n'
    for user_id, coin, last_alert, alert_threshold, interval in subs:
        answer += f'{markdown.bold(coin.upper())}\n'
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Изменить', callback_data=f"change:subscriptions")]
        ]
    )
    await message.answer(answer, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb)

@router.message(F.text == 'Новая подписка')
async def handle_add_new_sub(message: types.Message) -> None:
    """
    Добавляет новую подписку
    :param message: Сообщение
    :return: Ответное сообщение
    """
    logger.debug(f'Try to add new subs')
    await message.answer("Выберите криптовалюты для отслеживания:", reply_markup=gen_ticker_kb())

@router.message(F.text == 'Текущие цены')
async def handle_get_prices(message: types.Message) -> None:
    """
    Получает последние цены на монеты, на которые подписан юзер
    :param message:
    :return:
    """
    logger.debug(f'Try to get current prices')
    subs = await get_user_subscriptions(message.from_user.id)
    logger.debug(f'User\'s subs: {subs}')
    prices = await get_last_prices_for_subs_list(subs, 86400)
    logger.debug(f'Last prices: {prices}')
    answer = 'Текущие цены:\n'
    # prices = sorted(prices, key=lambda x: x[2])
    for price in prices:
        if price:
            current_price = price[0]  # Последняя цена из БД
            last_price = price[-1]  # Самая ранняя цена из БД, но не ранее 24 часов
            logger.debug(f'Current price for {current_price[0]} = {current_price[1]}, Last price = {last_price[1]}')
            diff = (current_price[1] - last_price[1]) / last_price[1] * 100
            diff_sign = f'👎' if diff < 0 else f'👍'
            answer += f'{diff_sign} {markdown.bold(current_price[0].upper())}:\nТекущая цена \- {markdown.code(f'${current_price[1]}')}\nИзменение за 24 часа \= {markdown.bold(f'{round(diff, 2)}%')}\n\n'
    if answer == f'Текущие цены:\n':
        await message.answer(f'Цены ещё не обновлены')
    else:
        await message.answer(answer, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=get_main_menu())

@router.message(F.text == 'Настройки')
async def handle_user_settings(message: types.Message) -> None:
    """
    Настройки юзера
    :param message:
    :return:
    """
    await message.answer(f'Настройки ещё не реализованы')

@router.callback_query(F.data.startswith('change:'))
async def callback_change_subscriptions(callback: types.CallbackQuery):
    """
    Изменяет список подписок
    :param callback:
    :return:
    """
    logger.debug(f'Try to get subs')
    subs = await get_user_subscriptions(callback.from_user.id)
    logger.debug(f'User\'s subs: {subs}')
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f'{coin}', callback_data=f"change_coin:{coin}")]
            for user_id, coin, last_alert, alert_threshold, interval in subs
        ]
    )
    await callback.message.answer(f'Какую подписку изменить?', reply_markup=kb)

@router.callback_query(F.data.startswith('delete:'))
async def callback_delete_subscription(callback: types.CallbackQuery):
    """
    Удаляет подписку
    :param callback:
    :return:
    """
    ticker = callback.data.split(":")[1]
    user_id = callback.from_user.id
    try:
        await delete_user_subscription(user_id, ticker)
        await delete_coins(ticker)
        await callback.message.answer(f'Подписка на {ticker} удалена', reply_markup=get_main_menu())
    except SQLError as error:
        await callback.answer(f'Ошибка при удалении:\n{error}')

@router.callback_query(F.data.startswith('change_coin:'))
async def callback_change_coin_settings(callback: types.CallbackQuery):
    """
    Изменяет настройки подписки
    :param callback:
    :return:
    """
    ticker = callback.data.split(":")[1]
    threshold, timeout = (await get_user_subscriptions_settings(callback.from_user.id, ticker))[0]
    timeout = int(timeout/3600)
    if (timeout < 1) or (timeout > 24):
        raise ValueError
    if (timeout == 1) or (timeout == 21):
        hours = 'час'
    elif (1 < timeout < 5) or (21 < timeout < 25):
        hours = 'часа'
    else:
        hours = 'часов'
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f'Порог для уведомлений, в процентах (сейчас {int(threshold)}%)', callback_data=f'manual_settings:threshold:{ticker}')],
            [InlineKeyboardButton(text=f'Таймаут уведомлений (сейчас {int(timeout)} {hours})', callback_data=f'manual_settings:timeout:{ticker}')],
            [InlineKeyboardButton(text=f'Удалить {ticker}', callback_data=f'delete:{ticker}')]
        ]
    )
    await callback.message.answer(
        text=f'Что изменить?',
        reply_markup=kb
    )

@router.callback_query(F.data.startswith('manual_settings:'))
async def callback_manual_coin_settings(callback: types.CallbackQuery, state:FSMContext):
    """
    Ручные настройки для подписки
    :param state:
    :param callback:
    :return:
    """
    action = callback.data.split(':')[1]
    ticker = callback.data.split(':')[2]
    answer = f'Введите пороговый процент для уведомлений (от 1 до 100):' if action == 'threshold' else f'Введите таймаут для уведомлений (в часах):'
    await state.set_data({'action': action, 'ticker': ticker})
    await callback.message.answer(answer)
    await state.set_state(SubscribeState.waiting_for_ticker_setting)

@router.message(SubscribeState.waiting_for_ticker_setting)
async def process_ticker_setting(message: types.Message, state: FSMContext):
    """
    Обработчик настроек подписки
    :param message:
    :param state:
    :return:
    """
    data = await state.get_data()
    action = data['action']
    ticker = data['ticker']
    value = message.text.strip().lower()
    try:
        value = int(value)
        current_threshold, current_timeout = (await get_user_subscriptions_settings(message.from_user.id, ticker))[0]
        answer = ''
        if action == 'threshold':
            if (value<1) or (value>100):
                raise ValueError
            await update_user_subscription(message.from_user.id, ticker, threshold=value, timeout=current_timeout)
            answer = f'Пороговый процент для {ticker} изменён, новое значение {value}%'
        elif action == 'timeout':
            if (value<1) or (value>24):
                raise ValueError
            timeout = value*60*60
            await update_user_subscription(message.from_user.id, ticker, timeout=timeout, threshold=current_threshold)
            if (value == 1) or (value == 21):
                hours = 'час'
            elif (1 < value < 5) or (21 < value < 25):
                hours = 'часа'
            else:
                hours = 'часов'
            answer = f'Таймаут для {ticker} изменён, новое значение {value} {hours}'
        await message.answer(answer, reply_markup=get_main_menu())
    except SQLError as error:
        await message.answer(f'Ошибка: {error}')
    except ValueError as error:
        if action == 'threshold':
            await message.answer(f'Неверное значение. Значение должно быть целым числом от 1 до 100')
        elif action == 'timeout':
            await message.answer(f'Неверное значение. Значение должно быть целым числом от 1 до 24')
    finally:
        await state.clear()