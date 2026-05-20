"""
Сервис для получения курсов валют ЦБРФ
"""
import asyncio

import cbrapi as cbr
from datetime import datetime, timezone, timedelta

from config.config import config
# from bot import TIME_ZONE
# TIME_ZONE=7


async def format_date(date: datetime):
    return date.strftime(format='%Y-%m-%d')


class CBRService:
    """
    Класс для работы с API ЦБ РФ
    """

    def __init__(self, symbol: str, period: str = 'D'):
        self.cbr = cbr
        self.symbol: str = symbol
        self.period: str = period
        self.rates: dict = {}

    async def get_current_rates(self) -> dict:
        """
        Обновляет текущие курсы валют
        Returns:
            Словарь с датами и курсами валют
        """
        result = {}
        start_period = await self.get_start_period()
        end_period = await self.get_end_period()
        time_series = self.cbr.get_time_series(self.symbol, await format_date(start_period), await format_date(end_period))

        for date, currency in time_series.items():
            result[f'{date}'] = f'{currency}'
        '''for index, currency in enumerate(time_series[::-1]):
            result[f'{format_date(self.end_period - timedelta(days=index))}'] = f'{currency}'''

        return result

    async def update_rates(self) -> None:
        """
        Обновляет переменную курсов валют
        Returns:
            None
        """
        self.rates = await self.get_current_rates()

    async def get_last_rate(self) -> str:
        """
        Получает последние изменения курса валют
        Returns:
            Строка с данными о курсах
        """
        if await self.is_updated():
            today_price = float(list(self.rates.values())[-2])
            tomorrow_price = float(list(self.rates.values())[-1])
            sign = f'✅' if tomorrow_price > today_price else f'❌'
            desc = f'Рост' if tomorrow_price > today_price else f'Падение'
            return f'❗ Курс {self.symbol} сегодня: {today_price:.2f}\n{sign} Курс {self.symbol} завтра: {tomorrow_price:.2f}\n{desc} на {abs(tomorrow_price-today_price):.2f} руб.'
        else:
            return f'Курс {self.symbol} не изменился\nТекущий курс ЦБ РФ: {float(list(self.rates.values())[-1]):.2f}'

    async def get_start_period(self) -> datetime:
        """
        Получает дату начального периода
        Returns:
            Дату начала периода
        """
        end_period = await self.get_end_period()
        if self.period == 'W':
            days = 7
        elif self.period == 'M':
            days = 30
        else:
            days = 1

        return end_period - timedelta(days=days)

    async def get_end_period(self) -> datetime:
        """
        Получает дату конечного периода
        Returns:
            Дату конечного периода
        """
        return datetime.now(tz=timezone(timedelta(hours=config.TIME_ZONE))) + timedelta(days=1)

    async def is_updated(self) -> bool:
        """
        Проверяет, есть ли обновление курса?
        Returns:
            Bool
        """
        end_period = await self.get_end_period()
        try:
            if self.rates[await format_date(end_period)] != self.rates[await format_date(end_period - timedelta(days=1))]:
                return True
        except KeyError:
            return False
        return False
