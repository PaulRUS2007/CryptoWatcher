from dotenv import load_dotenv
import os

load_dotenv()

class Config:

    BOT_TOKEN: str = os.getenv('TELEGRAM_API_KEY')
    LOG_LEVEL: str = os.getenv('LOG_LEVEL')
    TIME_ZONE: int = int(os.getenv('TIME_ZONE'))

config = Config()