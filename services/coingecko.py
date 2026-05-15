import aiohttp
from typing import Dict, List, Any

async def fetch_prices(tickers: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Получает текущие цены криптовалют через API CoinGecko
    
    Args:
        tickers: Список идентификаторов криптовалют для получения цен
        
    Returns:
        Словарь с ценами в формате {ticker: {"usd": price}}
        
    Raises:
        aiohttp.ClientError: При ошибке HTTP-запроса
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join(tickers),
        "vs_currencies": "usd"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            return await resp.json()


async def fetch_coins_list() -> List[Dict[str, str]]:
    """
    Получает полный список всех доступных криптовалют через API CoinGecko
    
    Returns:
        Список словарей с информацией о криптовалютах в формате:
        [{"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"}, ...]
        
    Raises:
        aiohttp.ClientError: При ошибке HTTP-запроса
    """
    url = "https://api.coingecko.com/api/v3/coins/list"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()