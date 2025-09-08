import aiosqlite
from coingecko import fetch_coins_list
import logging
import time
from typing import List, Tuple, Dict, Any, Optional, Union

DB_FILE = "db.sqlite"
logger = logging.getLogger(__name__)

async def init_db() -> None:
    """
    Инициализирует базу данных, создает необходимые таблицы
    и загружает список криптовалют если база пуста
    
    Returns:
        None
    """
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

async def add_user(user_id: int) -> None:
    """
    Добавляет нового пользователя в базу данных
    
    Args:
        user_id: Уникальный идентификатор пользователя Telegram
        
    Returns:
        None
    """
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        INSERT OR IGNORE INTO users (user_id)
        VALUES (?)
        """, (user_id,))
        await db.commit()

async def add_subscription(user_id: int, ticker: str, alert_threshold: int = 5, interval: int = 3600) -> None:
    """
    Добавляет новую подписку пользователя на криптовалюту
    
    Args:
        user_id: Идентификатор пользователя
        ticker: Тикер криптовалюты
        alert_threshold: Пороговое значение для уведомлений в процентах (по умолчанию 5%)
        interval: Интервал между уведомлениями в секундах (по умолчанию 3600)
        
    Returns:
        None
    """
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        INSERT INTO subscriptions (user_id, ticker, last_alert, alert_threshold, interval)
        VALUES (?, ?, ?, ?, ?)
        """, (user_id, ticker, time.time(), alert_threshold, interval))
        await db.commit()

async def get_user_subscriptions(user_id: int) -> List[Tuple[int, str, float, int, int]]:
    """
    Получает все подписки пользователя
    
    Args:
        user_id: Идентификатор пользователя
        
    Returns:
        Список кортежей с данными подписок:
        [(user_id, ticker, last_alert, alert_threshold, interval), ...]
    """
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT user_id, ticker, last_alert, alert_threshold, interval
        FROM subscriptions
        WHERE user_id = (?)
        """, (user_id,))
        return await cursor.fetchall()

async def get_user_subscriptions_by_ticker(ticker: str) -> List[Tuple[int, float, int, int]]:
    """
    Получает всех пользователей, подписанных на конкретную криптовалюту
    
    Args:
        ticker: Тикер криптовалюты
        
    Returns:
        Список кортежей с данными подписок:
        [(user_id, last_alert, alert_threshold, interval), ...]
    """
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT user_id, last_alert, alert_threshold, interval
        FROM subscriptions
        WHERE ticker = (?)
        """, (ticker, ))
        return await cursor.fetchall()

async def update_last_alert(user_id: int, ticker: str) -> None:
    """
    Обновляет время последнего уведомления для подписки
    
    Args:
        user_id: Идентификатор пользователя
        ticker: Тикер криптовалюты
        
    Returns:
        None
    """
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        UPDATE subscriptions
        SET last_alert = (?)
        WHERE user_id = (?) AND ticker = (?)
        """, (time.time(), user_id, ticker, ))
        await db.commit()

async def get_user(user_id: int) -> List[Tuple[int]]:
    """
    Проверяет существование пользователя в базе данных
    
    Args:
        user_id: Идентификатор пользователя
        
    Returns:
        Список кортежей с данными пользователя или пустой список
    """
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT user_id
        FROM users
        WHERE user_id = (?)
        """, (user_id,))
        return await cursor.fetchall()

async def add_coin(ticker: str) -> None:
    """
    Добавляет новую криптовалюту в список отслеживаемых
    
    Args:
        ticker: Тикер криптовалюты
        
    Returns:
        None
    """
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        INSERT INTO coins (ticker)
        VALUES (?)
        """, (ticker, ))
        await db.commit()

async def get_coins() -> List[Tuple[str]]:
    """
    Получает список всех отслеживаемых криптовалют
    
    Returns:
        Список кортежей с тикерами: [('bitcoin',), ('ethereum',), ...]
    """
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT ticker 
        FROM coins
        """)
        return await cursor.fetchall()

async def delete_coins(coin: str) -> None:
    """
    Удаляет криптовалюту из списка отслеживаемых, если на неё нет подписок
    
    Args:
        coin: Тикер криптовалюты для удаления
        
    Returns:
        None
    """
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT user_id
        FROM subscriptions
        WHERE ticker = (?)
        """, (coin, ))
        subs = await cursor.fetchall()
        print(f'Subs: {subs}')
        if not subs:
            await db.execute("""
            DELETE FROM coins
            WHERE ticker = (?)
            """, (coin, ))
            await db.commit()

async def add_coins_to_list(coins: Union[List[Tuple], List[Dict[str, str]]]) -> None:
    """
    Добавляет список криптовалют в справочник
    
    Args:
        coins: Список криптовалют в формате кортежей или словарей
        
    Returns:
        None
    """
    async with aiosqlite.connect(DB_FILE) as db:
        await db.executemany("""
        INSERT INTO coins_list (ticker, symbol, name)
        VALUES (:id, :symbol, :name)
        """, coins)
        await db.commit()

async def get_coins_from_list() -> List[Tuple[str, str, str]]:
    """
    Получает полный список криптовалют из справочника
    
    Returns:
        Список кортежей с данными криптовалют:
        [('bitcoin', 'btc', 'Bitcoin'), ...]
    """
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT ticker, symbol, name
        FROM coins_list
        """)
        return await cursor.fetchall()

async def get_coin_from_list(ticker: str) -> List[Tuple[str, str, str]]:
    """
    Ищет криптовалюту в справочнике по тикеру
    
    Args:
        ticker: Тикер криптовалюты для поиска
        
    Returns:
        Список кортежей с данными найденных криптовалют
    """
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
                            SELECT ticker, symbol, name
                            FROM coins_list
                            WHERE ticker = (?)
                            """, (ticker, ))
        return await cursor.fetchall()

async def add_prices(prices: Union[List[Tuple[str, float, int]], List[Dict[str, Any]]]) -> None:
    """
    Добавляет историю цен в базу данных
    
    Args:
        prices: Список данных о ценах в формате:
               [(ticker, price, timestamp), ...] или
               [{"ticker": "bitcoin", "price": 50000.0, "timestamp": 1234567890}, ...]
        
    Returns:
        None
    """
    async with aiosqlite.connect(DB_FILE) as db:
        await db.executemany("""
        INSERT INTO prices (ticker, price, timestamp)
        VALUES (:ticker, :price, :timestamp)
        """, prices)
        await db.commit()

async def get_last_prices_for_subs_list(subs: List[Tuple], period: int) -> List[List[Tuple[str, float, int]]]:
    """
    Получает историю цен за указанный период для списка подписок
    
    Args:
        subs: Список подписок пользователя
        period: Период в секундах для получения цен
        
    Returns:
        Список списков с историей цен для каждой подписки
    """
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

async def get_last_prices_for_ticker(ticker: str, period: int) -> List[Tuple[str, float, int]]:
    """
    Получает историю цен для конкретной криптовалюты за указанный период
    
    Args:
        ticker: Тикер криптовалюты
        period: Период в секундах
        
    Returns:
        Список кортежей с историей цен: [(ticker, price, timestamp), ...]
    """
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
    """
    Удаляет старые записи о ценах из базы данных
    
    Args:
        period: Возраст записей в секундах, старше которых нужно удалить
        
    Returns:
        None
    """
    now = time.time()
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        DELETE FROM prices
        WHERE timestamp < (?)
        """, (now-period, ))
        await db.commit()

async def delete_user_subscription(user_id: int, ticker: str) -> None:
    """
    Удаляет подписку пользователя на криптовалюту
    
    Args:
        user_id: Идентификатор пользователя
        ticker: Тикер криптовалюты
        
    Returns:
        None
    """
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        DELETE FROM subscriptions
        WHERE user_id = (?)
        AND ticker = (?)
        """, (user_id, ticker, ))
        await db.commit()

async def update_user_subscription(user_id: int, ticker: str, threshold: int = 1, timeout: int = 3600) -> None:
    """
    Обновляет настройки подписки пользователя
    
    Args:
        user_id: Идентификатор пользователя
        ticker: Тикер криптовалюты
        threshold: Новое пороговое значение в процентах
        timeout: Новый интервал уведомлений в секундах
        
    Returns:
        None
    """
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        UPDATE subscriptions
        SET alert_threshold = (?), interval = (?)
        WHERE user_id = (?)
        AND ticker = (?)
        """, (threshold, timeout, user_id, ticker))
        await db.commit()

async def get_user_subscriptions_settings(user_id: int, ticker: str) -> List[Tuple[int, int]]:
    """
    Получает настройки конкретной подписки пользователя
    
    Args:
        user_id: Идентификатор пользователя
        ticker: Тикер криптовалюты
        
    Returns:
        Список кортежей с настройками: [(alert_threshold, interval), ...]
    """
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
                SELECT alert_threshold, interval
                FROM subscriptions
                WHERE user_id = (?)
                AND ticker = (?)
                """, (user_id, ticker, ))
        return await cursor.fetchall()

async def get_max_interval_from_subscriptions() -> List[Tuple[Optional[int]]]:
    """
    Получает максимальный интервал уведомлений среди всех подписок
    
    Returns:
        Список кортежей с максимальным интервалом: [(max_interval,), ...]
    """
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
        SELECT MAX(interval)
        FROM subscriptions
        """)
        return await cursor.fetchall()