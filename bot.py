import asyncio
import logging
from aiogram import Bot, Dispatcher
from handlers import router
from scheduler import start_scheduler
from config.config import config

from typing import Optional


logger = logging.getLogger(__name__)


async def main() -> None:
    """
    Основная функция запуска бота
    
    Инициализирует бота, диспетчер, подключает роутеры и запускает планировщик задач.
    Затем начинает polling для получения обновлений от Telegram.
    
    Returns:
        None
    """
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await start_scheduler(bot) # запускам планировщик на каждые 60 секунд
    await dp.start_polling(bot)

if __name__ == "__main__":
    """
    Настраиваем логи и запускаем бота
    """
    logging.basicConfig(level=config.LOG_LEVEL)
    logger.info(f'Starting bot...')
    asyncio.run(main())
