import aiosqlite
from coingecko import fetch_coins_list
import logging
import time

DB_FILE = "db.sqlite"
logger = logging.getLogger(__name__)

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS subscriptions (user_id INTEGER, ticker TEXT, last_alert INTEGER)""")
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

async def add_subscription(user_id: int, ticker: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        INSERT INTO subscriptions (user_id, ticker, last_alert)
        VALUES (?, ?, ?)
        """, (user_id, ticker, time.time()))
        await db.commit()

async def get_user_subscriptions(user_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT user_id, ticker, last_alert
        FROM subscriptions
        WHERE user_id = (?)
        """, (user_id,))
        return await cursor.fetchall()

async def get_user_subscriptions_by_ticker(ticker: str) -> tuple:
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT user_id, last_alert
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

async def get_last_prices(subs: list, period: int) -> list:
    prices = []
    now = time.time()
    async with aiosqlite.connect(DB_FILE) as db:
        for item in subs:
            try:
                sub, ticker, last_alert = item
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