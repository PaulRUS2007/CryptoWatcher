import asyncio
import logging
from aiogram import Bot, Dispatcher
from handlers import router
from scheduler import start_scheduler
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger(__name__)
BOT_TOKEN = os.getenv(f'TELEGRAM_API_KEY')
LOG_LEVEL = os.getenv(f'LOG_LEVEL')

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await start_scheduler(bot) # запускам планировщик на каждые 60 секунд
    await dp.start_polling(bot)

if __name__ == "__main__":
    """
    Настраиваем логи и запускаем бота
    """
    logging.basicConfig(level=LOG_LEVEL)
    logger.info(f'Starting bot...')
    asyncio.run(main())
