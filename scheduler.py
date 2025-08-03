import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import get_coins, add_coins_to_list, get_coins_from_list, add_prices, get_last_prices, get_user_subscriptions_by_ticker, delete_old_prices, update_last_alert
from coingecko import fetch_prices, fetch_coins_list
from aiogram import Bot
from aiogram.enums.parse_mode import ParseMode
from aiogram.utils import markdown
import time

logger = logging.getLogger(__name__)
# Порог для алерта
ALERT_THRESHOLD = 0.05
# Интервал уведомлений
INTERVAL = 3600

async def get_subscribed_users(coins: list):
    """
    Получает список подписанных юзеров
    :param coins:
    :return:
    """
    user_map = {}
    tickers = set()
    for ticker in coins:  # получаем список юзеров, подписанных на обновления
        tickers.add(ticker[0])
        user_map[ticker[0]] = await get_user_subscriptions_by_ticker(ticker[0])
    return tickers, user_map

async def add_new_prices(prices: dict, now: time.time):
    """
    Получаем и добавляем в БД новые цены
    :param now:
    :param prices:
    :return:
    """
    new_prices = []
    for price in prices:
        usd = prices.get(price, {}).get('usd')
        if usd is None:
            continue
        new_prices.append((price, usd, now))
    await add_prices(new_prices)  # добавляем текущие цены в БД

async def send_message(bot: Bot, ticker: str, now: time.time, timestamp: time.time, users: dict, diff: int, current_price: int) -> None:
    """
    Отправляет алерт
    :param current_price:
    :param diff:
    :param bot:
    :param ticker:
    :param now:
    :param timestamp:
    :param users:
    :return:
    """
    change_time = int(round((now - timestamp) / 60, 0))
    change_text = ''
    if change_time == 1 or (change_time % 10 == 1 and change_time != 11):
        change_text = f'последнюю {change_time} минуту'
    elif 1 < change_time % 10 <= 4:
        change_text = f'последние {change_time} минуты'
    elif 4 < change_time % 10 <= 10 or change_time == 11 or change_time % 10 == 0:
        change_text = f'последние {change_time} минут'

    sign = "📈" if diff > 0 else "📉"
    diff_text = f'вырос' if diff > 0 else f'упал'
    msg = f'{sign} {markdown.bold(ticker.upper())} {markdown.bold(diff_text)} на {markdown.code(f'{diff}%')} за {change_text}\!\nТекущая цена: {markdown.code(f'${current_price}')}'
    # msg = Text.as_markdown(msg)
    logger.debug(f'Message to send: {msg}')
    for user, last_alert in users[ticker]:
        if now - last_alert > INTERVAL:
            await bot.send_message(user, msg, parse_mode=ParseMode.MARKDOWN_V2)
            await update_last_alert(user, ticker)

async def check_prices(bot: Bot):
    coins = await get_coins()
    logger.info(f'Coins for checking prices: {coins}')
    if not coins:
        return
    price_history = await get_last_prices(coins, 3600)
    logger.debug(f'Price history: {price_history}, type: {type(price_history)}')
    tickers, user_map = await get_subscribed_users(coins)
    logger.debug(f'User map: {user_map}')
    logger.debug(f'Tickers: {tickers}')
    prices = await fetch_prices(list(tickers))
    now = int(time.time())
    await add_new_prices(prices, now)
    for ticker in tickers:
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
                break


async def coins_list_worker() -> None:
    """
    Получаем список монет и сравниваем их с локальным. Если есть разница - обновляем локальный список
    :return:
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
    Очищает БД от старых цен
    :return:
    """
    await delete_old_prices(259200)

async def start_scheduler(bot: Bot):
    from database import init_db
    await init_db()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_prices, "interval", seconds=60, args=[bot])
    scheduler.add_job(coins_list_worker, 'interval', seconds=86400)
    scheduler.add_job(clear_db, 'interval', seconds=3600)
    scheduler.start()
