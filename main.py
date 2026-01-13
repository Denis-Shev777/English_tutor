import asyncio
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
import os

# Загружаем переменные окружения
load_dotenv()

# Импортируем handlers
from handlers import commands, conversation, payments

# Токен бота
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def main():
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрируем роутеры
    dp.include_router(commands.router)
    dp.include_router(payments.router)
    dp.include_router(conversation.router)
    
    print("🤖 Бот запущен!")
    
    # Запуск поллинга
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())