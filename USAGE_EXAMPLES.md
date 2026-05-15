# Примеры использования CryptoWatcher

## Быстрый старт

### 1. Установка и настройка

```bash
# Клонирование репозитория
git clone <repository-url>
cd CryptoWatcher

# Установка зависимостей
pip install -r requirements.txt

# Создание файла конфигурации
echo "TELEGRAM_API_KEY=your_bot_token_here" > .env
echo "LOG_LEVEL=INFO" >> .env

# Запуск бота
python bot.py
```

### 2. Первое использование

1. Найдите вашего бота в Telegram по имени
2. Отправьте команду `/start`
3. Выберите криптовалюты для отслеживания
4. Настройте параметры уведомлений

## Примеры команд

### Основные команды

#### /start
```
Пользователь: /start
Бот: Добро пожаловать! Выберите, что вы хотите сделать:
     [Текущие цены] [Мои подписки] [Новая подписка]
```

#### Просмотр текущих цен
```
Пользователь: Текущие цены
Бот: Текущие цены:
     👍 BITCOIN:
     Текущая цена - $45,230.50
     Изменение за 24 часа = +2.34%
     Минимум за 24 часа = $44,100.00
     Максимум за 24 часа = $45,500.00
     
     👎 ETHEREUM:
     Текущая цена - $3,200.75
     Изменение за 24 часа = -1.25%
     Минимум за 24 часа = $3,150.00
     Максимум за 24 часа = $3,300.00
```

#### Просмотр подписок
```
Пользователь: Мои подписки
Бот: Твои подписки:
     BITCOIN, текущие настройки: порог 5%, интервал 1 час
     ETHEREUM, текущие настройки: порог 3%, интервал 2 часа
     [Изменить]
```

### Добавление подписок

#### Через готовые кнопки
```
Пользователь: Новая подписка
Бот: Выберите криптовалюты для отслеживания:
     [BitCoin] [DogeCoin] [Ethereum] [Other]
     
Пользователь: [BitCoin]
Бот: Подписка добавлена!
     Вы подписались на bitcoin
```

#### Ручной ввод
```
Пользователь: Новая подписка
Бот: Выберите криптовалюты для отслеживания:
     [BitCoin] [DogeCoin] [Ethereum] [Other]
     
Пользователь: [Other]
Бот: Введи название монеты:

Пользователь: cardano
Бот: Подписка добавлена!
     Вы подписались на cardano
```

#### Поиск похожих криптовалют
```
Пользователь: [Other]
Бот: Введи название монеты:

Пользователь: bitcoi
Бот: Нет такой монеты
     Возможно имелось ввиду:
     [bitcoin] [bitcoin-cash] [bitcoin-gold]
```

### Управление подписками

#### Изменение настроек
```
Пользователь: [Изменить] (из "Мои подписки")
Бот: Какую подписку изменить?
     [BITCOIN] [ETHEREUM]

Пользователь: [BITCOIN]
Бот: Что изменить?
     [Порог для уведомлений]
     [Таймаут уведомлений]
     [Удалить bitcoin]

Пользователь: [Порог для уведомлений]
Бот: Введите пороговый процент для уведомлений (от 1 до 100):

Пользователь: 10
Бот: Пороговый процент для bitcoin изменён, новое значение 10%
```

#### Удаление подписки
```
Пользователь: [Удалить bitcoin]
Бот: Подписка на bitcoin удалена
```

## Примеры уведомлений

### Уведомление о росте цены
```
📈 BITCOIN вырос на 5.2% за последние 2 часа!
Текущая цена: $47,500.00
```

### Уведомление о падении цены
```
📉 ETHEREUM упал на 3.8% за последние 45 минут!
Текущая цена: $3,100.25
```

### Уведомление с детальным временем
```
📈 CARDANO вырос на 7.5% за последние 3 часа 15 минут!
Текущая цена: $0.85
```

## Примеры настройки

### Консервативная стратегия
- **Порог уведомлений:** 10%
- **Интервал:** 6 часов
- **Криптовалюты:** Bitcoin, Ethereum

### Агрессивная стратегия
- **Порог уведомлений:** 2%
- **Интервал:** 30 минут
- **Криптовалюты:** Множество альткоинов

### Долгосрочная стратегия
- **Порог уведомлений:** 20%
- **Интервал:** 24 часа
- **Криптовалюты:** Только крупные криптовалюты

## Примеры интеграции

### Использование в Python коде

```python
import asyncio
from services.coingecko import fetch_prices, fetch_coins_list
from database import add_user, add_subscription, get_user_subscriptions


async def example_usage():
    # Получение цен
    prices = await fetch_prices(['bitcoin', 'ethereum'])
    print(f"Bitcoin price: ${prices['bitcoin']['usd']}")

    # Получение списка криптовалют
    coins = await fetch_coins_list()
    print(f"Total coins available: {len(coins)}")

    # Работа с пользователями
    await add_user(12345)
    await add_subscription(12345, 'bitcoin', alert_threshold=5, interval=3600)

    # Получение подписок
    subs = await get_user_subscriptions(12345)
    print(f"User subscriptions: {subs}")


# Запуск примера
asyncio.run(example_usage())
```

### Использование API напрямую

```python
import aiohttp
import asyncio

async def direct_api_usage():
    # Прямой запрос к CoinGecko API
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin,ethereum", "vs_currencies": "usd"}
        ) as resp:
            data = await resp.json()
            print(f"API Response: {data}")

asyncio.run(direct_api_usage())
```

## Примеры конфигурации

### .env файл
```env
# Обязательные настройки
TELEGRAM_API_KEY=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Опциональные настройки
LOG_LEVEL=INFO
DB_FILE=db.sqlite
CLEANUP_INTERVAL=3600
PRICE_CHECK_INTERVAL=60
COINS_UPDATE_INTERVAL=86400
```

### Настройка логирования
```python
import logging

# Настройка детального логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
```

## Примеры развертывания

### Локальная разработка
```bash
# Установка в виртуальном окружении
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

pip install -r requirements.txt
python bot.py
```

### Docker развертывание
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "bot.py"]
```

```bash
# Сборка и запуск
docker build -t crypto-watcher .
docker run -d --name crypto-bot \
  -e TELEGRAM_API_KEY=your_token \
  -v $(pwd)/data:/app/data \
  crypto-watcher
```

### Systemd сервис
```ini
[Unit]
Description=CryptoWatcher Bot
After=network.target

[Service]
Type=simple
User=crypto
WorkingDirectory=/opt/crypto-watcher
ExecStart=/opt/crypto-watcher/venv/bin/python bot.py
Restart=always
Environment=TELEGRAM_API_KEY=your_token

[Install]
WantedBy=multi-user.target
```

## Примеры мониторинга

### Проверка состояния бота
```python
import aiohttp
import asyncio

async def check_bot_health():
    """Проверка работоспособности бота"""
    try:
        # Проверка подключения к Telegram API
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.telegram.org/bot{TELEGRAM_API_KEY}/getMe"
            ) as resp:
                if resp.status == 200:
                    print("✅ Telegram API доступен")
                else:
                    print("❌ Telegram API недоступен")
        
        # Проверка подключения к CoinGecko API
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.coingecko.com/api/v3/ping"
            ) as resp:
                if resp.status == 200:
                    print("✅ CoinGecko API доступен")
                else:
                    print("❌ CoinGecko API недоступен")
                    
    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")

asyncio.run(check_bot_health())
```

### Логирование производительности
```python
import time
import logging

def performance_monitor(func):
    """Декоратор для мониторинга производительности"""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        
        logging.info(
            f"Function {func.__name__} executed in {end_time - start_time:.2f}s"
        )
        return result
    return wrapper

# Использование
@performance_monitor
async def check_prices(bot):
    # ... код функции
    pass
```

## Примеры тестирования

### Unit тесты
```python
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from handlers import cmd_start
from database import add_user

@pytest.mark.asyncio
async def test_cmd_start_new_user():
    """Тест команды /start для нового пользователя"""
    # Мок сообщения
    message = AsyncMock()
    message.from_user.id = 12345
    
    # Мок базы данных
    with patch('handlers.get_user', return_value=[]):
        with patch('handlers.add_user', new_callable=AsyncMock):
            await cmd_start(message)
            
            # Проверяем, что пользователь был добавлен
            message.answer.assert_called()
            assert "Выберите криптовалюты" in str(message.answer.call_args)
```

### Интеграционные тесты
```python
import pytest
from database import init_db, add_user, get_user

@pytest.mark.asyncio
async def test_user_workflow():
    """Тест полного цикла работы с пользователем"""
    # Инициализация тестовой БД
    await init_db()
    
    # Добавление пользователя
    await add_user(12345)
    
    # Проверка добавления
    user = await get_user(12345)
    assert len(user) == 1
    assert user[0][0] == 12345
```

## Примеры расширения функциональности

### Добавление новых команд
```python
from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    """Показывает справку по командам"""
    help_text = """
    Доступные команды:
    /start - Начать работу с ботом
    /help - Показать эту справку
    /stats - Показать статистику
    """
    await message.answer(help_text)

@router.message(Command("stats"))
async def cmd_stats(message: types.Message) -> None:
    """Показывает статистику пользователя"""
    # Получение статистики из БД
    subs = await get_user_subscriptions(message.from_user.id)
    
    stats_text = f"""
    Ваша статистика:
    • Подписок: {len(subs)}
    • Активных уведомлений: {sum(1 for sub in subs if sub[3] > 0)}
    """
    await message.answer(stats_text)
```

### Добавление новых источников данных
```python
# Новый модуль для работы с другим API
import aiohttp
from typing import Dict, List

async def fetch_prices_from_binance(tickers: List[str]) -> Dict[str, float]:
    """Получение цен с Binance API"""
    url = "https://api.binance.com/api/v3/ticker/price"
    
    async with aiohttp.ClientSession() as session:
        prices = {}
        for ticker in tickers:
            async with session.get(url, params={"symbol": f"{ticker.upper()}USDT"}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    prices[ticker] = float(data["price"])
        return prices
```
