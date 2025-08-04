import asyncio
import logging
from aiogram import Bot, Dispatcher
from handlers import router
from scheduler import start_scheduler

logger = logging.getLogger(__name__)
BOT_TOKEN = ""

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    # await set_main_menu(bot)
    await start_scheduler(bot) # запускам планировщик на каждые 60 секунд
    await dp.start_polling(bot)

if __name__ == "__main__":
    """
    Настраиваем логи и запускаем бота
    """
    logging.basicConfig(level=logging.INFO)
    logger.info(f'Starting bot...')
    asyncio.run(main())
