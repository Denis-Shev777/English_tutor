import asyncio
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
import os

# Загружаем переменные окружения
load_dotenv()

# Импортируем логгер и handlers
from logger import get_logger
from handlers import commands, conversation, payments
from database import init_db

# Логгер
logger = get_logger('main')

# Токен бота
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def main():
    # Инициализация базы данных
    try:
        init_db()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        return

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Регистрируем роутеры
    dp.include_router(commands.router)
    dp.include_router(payments.router)
    dp.include_router(conversation.router)

    logger.info("🤖 Бот запущен и готов к работе!")

    try:
        # Запуск поллинга
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Критическая ошибка при работе бота: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())