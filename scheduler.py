import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import get_coins, add_coins_to_list, get_coins_from_list, add_prices, get_last_prices_for_subs_list, get_user_subscriptions_by_ticker, delete_old_prices, update_last_alert, get_max_interval_from_subscriptions, get_last_prices_for_ticker
from coingecko import fetch_prices, fetch_coins_list
from aiogram import Bot
from aiogram.enums.parse_mode import ParseMode
from aiogram.utils import markdown
import time
from typing import List, Dict, Tuple, Set, Any

logger = logging.getLogger(__name__)
# Порог для алерта
# ALERT_THRESHOLD = 0.01
# Интервал уведомлений
# INTERVAL = 3600

async def get_subscribed_users(coins: List[Tuple[str]]) -> Tuple[Set[str], Dict[str, List[Tuple[int, float, int, int]]]]:
    """
    Получает список пользователей, подписанных на отслеживаемые криптовалюты
    
    Args:
        coins: Список отслеживаемых криптовалют
        
    Returns:
        Кортеж из множества тикеров и словаря с подписками пользователей
    """
    user_map: Dict[str, List[Tuple[int, float, int, int]]] = {}
    tickers: Set[str] = set()
    for ticker in coins:  # получаем список юзеров, подписанных на обновления
        tickers.add(ticker[0])
        user_map[ticker[0]] = await get_user_subscriptions_by_ticker(ticker[0])
    return tickers, user_map

async def add_new_prices(prices: Dict[str, Dict[str, float]], now: float) -> None:
    """
    Добавляет новые цены криптовалют в базу данных
    
    Args:
        prices: Словарь с ценами в формате {ticker: {"usd": price}}
        now: Текущее время в формате timestamp
        
    Returns:
        None
    """
    new_prices = []
    for price in prices:
        usd = prices.get(price, {}).get('usd')
        if usd is None:
            continue
        new_prices.append((price, usd, now))
    await add_prices(new_prices)  # добавляем текущие цены в БД

async def send_message(bot: Bot, ticker: str, now: float, timestamp: float, subscription: List[Tuple[int, float, int, int]], diff: float, current_price: float) -> None:
    """
    Отправляет уведомление пользователям о значительном изменении цены
    
    Args:
        bot: Экземпляр Telegram бота
        ticker: Тикер криптовалюты
        now: Текущее время
        timestamp: Время последнего изменения цены
        subscription: Список подписок пользователей
        diff: Процент изменения цены
        current_price: Текущая цена
        
    Returns:
        None
    """
    change_time = int(round((now - timestamp) / 60, 0))
    change_hours = int(change_time // 60)
    change_minutes = int(change_time % 60)
    change_text = ''
    change_text_hours = ''
    if change_hours == 1 or change_hours == 21 and change_hours != 11:
        change_text_hours = f'последний {change_hours} час'
    elif 1 < change_hours % 10  <= 4 and (change_hours < 10 or change_hours > 20):
        change_text_hours = f'последние {change_hours} часа'
    elif 4 < change_hours % 10 <= 10 or change_hours == 11 or change_hours % 10 == 0 or (11 < change_hours <= 14):
        change_text_hours = f'последние {change_hours} часов'
    if change_minutes == 1 or (change_minutes % 10 == 1 and change_minutes != 11):
        change_text = f'последнюю {change_minutes} минуту' if change_hours == 0 else f'{change_text_hours} {change_minutes} минуту'
    elif 1 < change_minutes % 10 <= 4 and (change_minutes < 10 or change_minutes > 20):
        change_text = f'последние {change_minutes} минуты' if change_hours == 0 else f'{change_text_hours} {change_minutes} минуты'
    elif 4 < change_minutes % 10 <= 10 or change_minutes == 11 or change_minutes % 10 == 0 or (11 < change_minutes <= 14):
        change_text = f'последние {change_minutes} минут' if change_hours == 0 else f'{change_text_hours} {change_minutes} минут'

    sign = "📈" if diff > 0 else "📉"
    diff_text = 'вырос' if diff > 0 else 'упал'
    msg = f'{sign} {markdown.bold(ticker.upper())} {markdown.bold(diff_text)} на {markdown.code(f'{diff}%')} за {change_text}\!\nТекущая цена: {markdown.code(f'${current_price}')}'
    logger.debug(f'Message to send: {msg}')
    for user, last_alert, alert_threshold, interval in subscription:
        if now - last_alert > interval:
            await bot.send_message(user, msg, parse_mode=ParseMode.MARKDOWN_V2)
            await update_last_alert(user, ticker)

async def check_prices(bot: Bot) -> None:
    """
    Основная функция проверки цен и отправки уведомлений
    
    Получает текущие цены, сравнивает с историческими данными
    и отправляет уведомления при превышении пороговых значений
    
    Args:
        bot: Экземпляр Telegram бота
        
    Returns:
        None
    """
    coins = await get_coins()
    logger.info(f'Coins for checking prices: {coins}')
    if not coins:
        return
    tickers, user_map = await get_subscribed_users(coins)
    # interval = (await get_max_interval_from_subscriptions())[0][0]
    # price_history = await get_last_prices_for_subs_list(coins, interval)
    # logger.debug(f'Price history: {price_history}, type: {type(price_history)}')
    logger.debug(f'User map: {user_map}')
    logger.debug(f'Tickers: {tickers}')
    prices = await fetch_prices(list(tickers))
    now = int(time.time())
    await add_new_prices(prices, now)
    for ticker, sub in user_map.items():
        threshold = (sub[0][2]) / 100
        interval = sub[0][3]
        price_history = await get_last_prices_for_ticker(ticker, interval)
        current_price = prices.get(ticker, {}).get('usd')
        if current_price is None:
            continue
        # history = [x for y in price_history for x in y if ticker in x]
        for ticker_name, price, timestamp in price_history:
            if abs(current_price - price)/price > threshold:
                diff = round((current_price - price)/price * 100, 2)
                await send_message(
                    bot=bot,
                    ticker=ticker,
                    now=now,
                    timestamp=timestamp,
                    subscription=sub,
                    diff=diff,
                    current_price=current_price,
                )
                break

"""    for ticker in tickers:
        current_price = prices.get(ticker, {}).get('usd')
        if current_price is None:
            continue
        history = [x for y in price_history for x in y if ticker in x]
        for ticker_name, price, timestamp in history:
            if abs(current_price - price)/price > ALERT_THRESHOLD:
                diff = round((current_price - price)/price * 100, 2)
                await send_message(
                    bot=bot,
                    ticker=ticker,
                    now=now,
                    timestamp=timestamp,
                    users=user_map,
                    diff=diff,
                    current_price=current_price,
                )
                break"""


async def coins_list_worker() -> None:
    """
    Обновляет локальный список криптовалют из API CoinGecko
    
    Сравнивает локальный список с API и добавляет новые криптовалюты
    
    Returns:
        None
    """
    local_coins_list = await get_coins_from_list()
    api_coins_list = await fetch_coins_list()
    api_coins_list = [tuple(d.values()) for d in api_coins_list]
    diff = list(set(api_coins_list) - set(local_coins_list))
    logger.info(f'Diff of local and api = {diff}')
    if diff:
        await add_coins_to_list(diff)
        logger.info(f'Added new coins {diff} to DB')

async def clear_db() -> None:
    """
    Очищает базу данных от старых записей о ценах
    
    Удаляет записи старше 3 дней (259200 секунд)
    
    Returns:
        None
    """
    await delete_old_prices(259200)

async def start_scheduler(bot: Bot) -> None:
    """
    Запускает планировщик задач для фоновых операций
    
    Инициализирует базу данных и настраивает периодические задачи:
    - Проверка цен каждые 60 секунд
    - Обновление списка криптовалют каждые 24 часа
    - Очистка старых данных каждый час
    
    Args:
        bot: Экземпляр Telegram бота
        
    Returns:
        None
    """
    from database import init_db
    await init_db()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_prices, "interval", seconds=60, args=[bot])
    scheduler.add_job(coins_list_worker, 'interval', seconds=86400)
    scheduler.add_job(clear_db, 'interval', seconds=3600)
    scheduler.start()
