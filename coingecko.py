import aiohttp

async def fetch_prices(tickers: list[str]):
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join(tickers),
        "vs_currencies": "usd"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            return await resp.json()


async def fetch_coins_list() -> dict:
    """
    Получаем весь список монет
    :return: Dict
    """
    url = "https://api.coingecko.com/api/v3/coins/list"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()