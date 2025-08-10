import aiosqlite
from coingecko import fetch_coins_list
import logging
import time

DB_FILE = "db.sqlite"
logger = logging.getLogger(__name__)

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS subscriptions (user_id INTEGER, ticker TEXT, last_alert INTEGER, alert_threshold INTEGER, interval INTEGER)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS prices (ticker TEXT, price REAL, timestamp INTEGER)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS coins (id INTEGER PRIMARY KEY, ticker TEXT)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS coins_list (id INTEGER PRIMARY KEY, ticker TEXT, symbol TEXT, name TEXT)""")
        local_coins_list = await get_coins_from_list()
        if not local_coins_list:
            api_coins_list = await fetch_coins_list()
            logger.debug(f'Local coins list is empty')
            logger.debug(f'Type of api list: {type(api_coins_list)}')
            await add_coins_to_list(api_coins_list)
        await db.commit()

async def add_user(user_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        INSERT OR IGNORE INTO users (user_id)
        VALUES (?)
        """, (user_id,))
        await db.commit()

async def add_subscription(user_id: int, ticker: str, alert_threshold: int = 5, interval: int = 3600):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        INSERT INTO subscriptions (user_id, ticker, last_alert, alert_threshold, interval)
        VALUES (?, ?, ?, ?, ?)
        """, (user_id, ticker, time.time(), alert_threshold, interval))
        await db.commit()

async def get_user_subscriptions(user_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT user_id, ticker, last_alert, alert_threshold, interval
        FROM subscriptions
        WHERE user_id = (?)
        """, (user_id,))
        return await cursor.fetchall()

async def get_user_subscriptions_by_ticker(ticker: str) -> tuple:
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT user_id, last_alert, alert_threshold, interval
        FROM subscriptions
        WHERE ticker = (?)
        """, (ticker, ))
        return await cursor.fetchall()

async def update_last_alert(user_id: int, ticker: str) -> None:
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        UPDATE subscriptions
        SET last_alert = (?)
        WHERE user_id = (?) AND ticker = (?)
        """, (time.time(), user_id, ticker, ))
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT user_id
        FROM users
        WHERE user_id = (?)
        """, (user_id,))
        return await cursor.fetchall()

async def add_coin(ticker: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        INSERT INTO coins (ticker)
        VALUES (?)
        """, (ticker, ))
        await db.commit()

async def get_coins():
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT ticker 
        FROM coins
        """)
        return await cursor.fetchall()

async def delete_coins(coin: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        DELETE FROM coins
        WHERE ticker = (?)
        """, (coin, ))
        await db.commit()

async def add_coins_to_list(coins: list[tuple] or dict):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.executemany("""
        INSERT INTO coins_list (ticker, symbol, name)
        VALUES (:id, :symbol, :name)
        """, coins)
        await db.commit()

async def get_coins_from_list():
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT ticker, symbol, name
        FROM coins_list
        """)
        return await cursor.fetchall()

async def get_coin_from_list(ticker: str):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
                            SELECT ticker, symbol, name
                            FROM coins_list
                            WHERE ticker = (?)
                            """, (ticker, ))
        return await cursor.fetchall()

async def add_prices(prices: list or dict):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.executemany("""
        INSERT INTO prices (ticker, price, timestamp)
        VALUES (:ticker, :price, :timestamp)
        """, prices)
        await db.commit()

async def get_last_prices_for_subs_list(subs: list, period: int) -> list:
    prices = []
    now = time.time()
    async with aiosqlite.connect(DB_FILE) as db:
        for item in subs:
            try:
                sub, ticker, last_alert, alert_threshold, interval = item
            except ValueError:
                ticker = item[0]
            cursor = await db.execute("""
            SELECT ticker, price, timestamp
            FROM prices
            WHERE ticker = (?)
            AND timestamp BETWEEN (?) AND (?)
            ORDER BY timestamp DESC
            """, (ticker, now-period, now))
            prices.append(await cursor.fetchall())
    return prices

async def get_last_prices_for_ticker(ticker: str, period: int):
    now = time.time()
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
                    SELECT ticker, price, timestamp
                    FROM prices
                    WHERE ticker = (?)
                    AND timestamp BETWEEN (?) AND (?)
                    ORDER BY timestamp DESC
                    """, (ticker, now - period, now))
        return await cursor.fetchall()

async def delete_old_prices(period: int) -> None:
    now = time.time()
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        DELETE FROM prices
        WHERE timestamp < (?)
        """, (now-period, ))
        await db.commit()

async def delete_user_subscription(user_id: int, ticker: str) -> None:
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        DELETE FROM subscriptions
        WHERE user_id = (?)
        AND ticker = (?)
        """, (user_id, ticker, ))
        await db.commit()

async def update_user_subscription(user_id: int, ticker: str, threshold: int = 1, timeout: int = 3600):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        UPDATE subscriptions
        SET alert_threshold = (?), interval = (?)
        WHERE user_id = (?)
        AND ticker = (?)
        """, (threshold, timeout, user_id, ticker))
        await db.commit()

async def get_user_subscriptions_settings(user_id: int, ticker: str):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
                SELECT alert_threshold, interval
                FROM subscriptions
                WHERE user_id = (?)
                AND ticker = (?)
                """, (user_id, ticker, ))
        return await cursor.fetchall()

async def get_max_interval_from_subscriptions():
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT MAX(interval)
        FROM subscriptions
        """)
        return await cursor.fetchall()