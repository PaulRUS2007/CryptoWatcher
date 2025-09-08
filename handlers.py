import logging
from difflib import get_close_matches
from typing import List, Dict, Any, Optional

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
    Создает главное меню бота с основными кнопками
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопками главного меню
    """
    keyboard = [
        [KeyboardButton(text='Текущие цены')],
        [KeyboardButton(text='Мои подписки'),KeyboardButton(text='Новая подписка')],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder='Выбери действие',
        is_persistent=True,
    )

def gen_ticker_kb() -> InlineKeyboardMarkup:
    """
    Создает инлайн клавиатуру с доступными криптовалютами для подписки
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками криптовалют
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=ticker, callback_data=f"sub:{slug}")]
            for ticker, slug in available_tickers.items()
        ]
    )

async def check_ticker_in_db(slug: str) -> bool:
    """
    Проверяет, есть ли уже такой тикер в базе данных
    
    Args:
        slug: Идентификатор криптовалюты
        
    Returns:
        bool: True если тикер найден в БД, False в противном случае
    """
    tickers = await get_coins()
    for ticker in tickers:
        if ticker[0] == slug:
            return True
    return False

async def check_subscription(user_id: int, slug: str) -> bool:
    """
    Проверяет, подписан ли пользователь на указанную криптовалюту
    
    Args:
        user_id: Идентификатор пользователя
        slug: Идентификатор криптовалюты
        
    Returns:
        bool: True если пользователь подписан, False в противном случае
    """
    subs = await get_user_subscriptions(user_id)
    for user_id, coin, last_alert, alert_threshold, interval in subs:
        if coin == slug:
            return True
    return False

async def add_sub_to_db(user_id: int, slug: str) -> bool:
    """
    Добавляет подписку пользователя на криптовалюту в базу данных
    
    Args:
        user_id: Идентификатор пользователя
        slug: Идентификатор криптовалюты
        
    Returns:
        bool: True если подписка была добавлена, False если уже существовала
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
async def cmd_start(message: types.Message) -> None:
    """
    Обработчик команды /start
    
    Регистрирует нового пользователя или приветствует существующего
    
    Args:
        message: Объект сообщения от пользователя
        
    Returns:
        None
    """
    try:
        user = await get_user(message.from_user.id)
        logger.debug(f'User is {user}')
        if not user:
            await add_user(message.from_user.id)
            await message.answer("Выберите криптовалюты для отслеживания:", reply_markup=gen_ticker_kb())
        else:
            await message.answer('Добро пожаловать! Выберите, что вы хотите сделать:', reply_markup=get_main_menu())
    except SQLError as error:
        logger.error(f'Error: {error}')

@router.callback_query(F.data.startswith("sub:"))
async def callback_subscribe(callback: types.CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик callback-запросов для добавления подписок
    
    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
        
    Returns:
        None
    """
    slug = callback.data.split(":")[1]
    if slug == 'other': # проверяем ручной ввод
        await callback.message.answer('Введи название монеты:')
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
    await callback.message.answer('Добро пожаловать! Выберите, что вы хотите сделать:',
                                      reply_markup=get_main_menu())

@router.message(SubscribeState.waiting_for_ticker)
async def process_manual_ticker(message: types.Message, state: FSMContext) -> None:
    """
    Обработчик ручного ввода названия криптовалюты
    
    Args:
        message: Сообщение с названием криптовалюты
        state: Контекст состояния FSM
        
    Returns:
        None
    """
    ticker = message.text.strip().lower()
    success = False
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
        success = True
    except SQLError as error:
        coins = await get_coins_from_list()
        coins_list = []
        for coin in coins:
            coins_list.append(coin[0])
        similar = get_close_matches(message.text.strip().lower(), coins_list)
        await message.answer('Нет такой монеты')
        # await message.reply(f'Возможно имелось ввиду {similar[0]}?')
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=s, callback_data=f"sub:{s}")]
                for s in similar
            ]
        )
        await message.reply('Возможно имелось ввиду:', reply_markup=kb)
    finally:
        if success:
            await state.clear()
        else:
            return
        # await state.set_state(SubscribeState.waiting_for_ticker)

@router.message(F.text=='Мои подписки')
async def handle_my_subs(message: types.Message) -> None:
    """
    Показывает все подписки пользователя с их настройками
    
    Args:
        message: Сообщение от пользователя
        
    Returns:
        None
    """
    logger.debug(f'Try to get subs')
    subs = await get_user_subscriptions(message.from_user.id)
    logger.debug(f'User\'s subs: {subs}')
    answer = ''
    answer += 'Твои подписки:\n'
    for user_id, coin, last_alert, alert_threshold, interval in subs:
        interval = int(interval / 3600)
        change_text_hours = ''
        if interval == 1 or interval == 21 and interval != 11:
            change_text_hours = f'{interval} час'
        elif 1 < interval % 10 <= 4 and (interval < 10 or interval > 20):
            change_text_hours = f'{interval} часа'
        elif 4 < interval % 10 <= 10 or interval == 11 or interval % 10 == 0 or (11 < interval <= 14):
            change_text_hours = f'{interval} часов'
        answer += f'{markdown.bold(coin.upper())}, текущие настройки: порог {markdown.code(f'{alert_threshold}%')}, интервал {markdown.code(f'{change_text_hours}')}\n'
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Изменить', callback_data=f"change:subscriptions")]
        ]
    )
    await message.answer(answer, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb)

@router.message(F.text == 'Новая подписка')
async def handle_add_new_sub(message: types.Message) -> None:
    """
    Показывает интерфейс для добавления новой подписки
    
    Args:
        message: Сообщение от пользователя
        
    Returns:
        None
    """
    logger.debug(f'Try to add new subs')
    await message.answer("Выберите криптовалюты для отслеживания:", reply_markup=gen_ticker_kb())

@router.message(F.text == 'Текущие цены')
async def handle_get_prices(message: types.Message) -> None:
    """
    Показывает текущие цены и статистику по подписанным криптовалютам
    
    Args:
        message: Сообщение от пользователя
        
    Returns:
        None
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
            min_price = min(price, key=lambda item: item[1])
            max_price = max(price, key=lambda item: item[1])
            logger.debug(f'Current price for {current_price[0]} = {current_price[1]}, Last price = {last_price[1]}')
            diff = (current_price[1] - last_price[1]) / last_price[1] * 100
            diff_sign = '👎' if diff < 0 else '👍'
            answer += (f'{diff_sign} {markdown.bold(current_price[0].upper())}:\n'
                       f'Текущая цена \- {markdown.code(f'${current_price[1]}')}\n'
                       f'Изменение за 24 часа \= {markdown.bold(f'{round(diff, 2)}%')}\n'
                       f'Минимум за 24 часа \= {markdown.code(f'${min_price[1]}')}\n'
                       f'Максимум за 24 часа \= {markdown.code(f'${max_price[1]}')}\n\n')
    if answer == 'Текущие цены:\n':
        await message.answer('Цены ещё не обновлены')
    else:
        await message.answer(answer, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=get_main_menu())

@router.message(F.text == 'Настройки')
async def handle_user_settings(message: types.Message) -> None:
    """
    Обработчик настроек пользователя (пока не реализован)
    
    Args:
        message: Сообщение от пользователя
        
    Returns:
        None
    """
    await message.answer('Настройки ещё не реализованы')

@router.callback_query(F.data.startswith('change:'))
async def callback_change_subscriptions(callback: types.CallbackQuery) -> None:
    """
    Показывает интерфейс для изменения подписок
    
    Args:
        callback: Объект callback-запроса
        
    Returns:
        None
    """
    logger.debug(f'Try to get subs')
    subs = await get_user_subscriptions(callback.from_user.id)
    logger.debug(f'User\'s subs: {subs}')
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f'{coin.upper()}', callback_data=f"change_coin:{coin}")]
            for user_id, coin, last_alert, alert_threshold, interval in subs
        ]
    )
    await callback.message.answer('Какую подписку изменить?', reply_markup=kb)

@router.callback_query(F.data.startswith('delete:'))
async def callback_delete_subscription(callback: types.CallbackQuery) -> None:
    """
    Удаляет подписку пользователя на криптовалюту
    
    Args:
        callback: Объект callback-запроса
        
    Returns:
        None
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
async def callback_change_coin_settings(callback: types.CallbackQuery) -> None:
    """
    Показывает интерфейс для изменения настроек конкретной подписки
    
    Args:
        callback: Объект callback-запроса
        
    Returns:
        None
    """
    ticker = callback.data.split(":")[1]
    threshold, timeout = (await get_user_subscriptions_settings(callback.from_user.id, ticker))[0]
    timeout = int(timeout/3600)
    if (timeout < 1) or (timeout > 24):
        raise ValueError
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Порог для уведомлений', callback_data=f'manual_settings:threshold:{ticker}')],
            [InlineKeyboardButton(text='Таймаут уведомлений', callback_data=f'manual_settings:timeout:{ticker}')],
            [InlineKeyboardButton(text=f'Удалить {ticker}', callback_data=f'delete:{ticker}')]
        ]
    )
    await callback.message.answer(
        text='Что изменить?',
        reply_markup=kb
    )

@router.callback_query(F.data.startswith('manual_settings:'))
async def callback_manual_coin_settings(callback: types.CallbackQuery, state: FSMContext) -> None:
    """
    Настраивает ручной ввод параметров подписки
    
    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
        
    Returns:
        None
    """
    action = callback.data.split(':')[1]
    ticker = callback.data.split(':')[2]
    answer = 'Введите пороговый процент для уведомлений (от 1 до 100):' if action == 'threshold' else 'Введите таймаут для уведомлений (в часах):'
    await state.set_data({'action': action, 'ticker': ticker})
    await callback.message.answer(answer)
    await state.set_state(SubscribeState.waiting_for_ticker_setting)

@router.message(SubscribeState.waiting_for_ticker_setting)
async def process_ticker_setting(message: types.Message, state: FSMContext) -> None:
    """
    Обрабатывает введенные пользователем настройки подписки
    
    Args:
        message: Сообщение с настройкой
        state: Контекст состояния FSM
        
    Returns:
        None
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
            await message.answer('Неверное значение. Значение должно быть целым числом от 1 до 100')
        elif action == 'timeout':
            await message.answer('Неверное значение. Значение должно быть целым числом от 1 до 24')
    finally:
        await state.clear()