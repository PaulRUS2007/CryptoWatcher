import logging
from difflib import get_close_matches

from aiogram import Router, types, F
from aiogram.filters import Command

from database import add_user, add_subscription, get_user_subscriptions, get_user, add_coin, get_coins, get_last_prices, get_coin_from_list, get_coins_from_list, delete_user_subscription
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

def get_main_menu() -> ReplyKeyboardMarkup:
    """
    Настраиваем кнопки главного меню бота
    :return: ReplyKeyboardMarkup
    """
    keyboard = [
        [KeyboardButton(text=f'Текущие цены')],
        [KeyboardButton(text=f'Мои подписки')],
        [KeyboardButton(text=f'Новая подписка')],
        [KeyboardButton(text=f'Настройки')],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder=f'Выбери действие'
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
    for user_id, coin, last_alert in subs:
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
    for user_id, coin, last_alert in subs:
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
    prices = await get_last_prices(subs, 86400)
    logger.debug(f'Last prices: {prices}')
    answer = 'Текущие цены:\n'
    # prices = sorted(prices, key=lambda x: x[2])
    for price in prices:
        current_price = price[0]  # Последняя цена из БД
        last_price = price[-1]  # Самая ранняя цена из БД, но не ранее 24 часов
        logger.debug(f'Current price for {current_price[0]} = {current_price[1]}, Last price = {last_price[1]}')
        diff = (current_price[1] - last_price[1])/last_price[1] * 100
        diff_sign = f'👎' if diff < 0 else f'👍'
        answer += f'{diff_sign} {markdown.bold(current_price[0].upper())}:\nТекущая цена \- {markdown.code(f'${current_price[1]}')}\nИзменение за 24 часа \= {markdown.bold(f'{round(diff, 2)}%')}\n\n'
    await message.answer(answer, parse_mode=ParseMode.MARKDOWN_V2)

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
    subs = await get_user_subscriptions(callback.message.from_user.id)
    logger.debug(f'User\'s subs: {subs}')
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f'{coin}', callback_data=f"delete:{coin}")]
            for user_id, coin, last_alert in subs
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
    user_id = callback.message.from_user.id
    try:
        await delete_user_subscription(user_id, ticker)
        await callback.message.answer(f'Подписка на {ticker} удалена')
    except SQLError as error:
        await callback.answer(f'Ошибка при удалении:\n{error}')