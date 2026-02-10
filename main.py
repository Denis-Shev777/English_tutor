import asyncio
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from database import init_db, ensure_columns
import os

load_dotenv()

from logger import get_logger
from handlers import commands, conversation, payments, onboarding
from handlers import topics, quiz
from database import init_db
# from payment_checker import start_payment_checker  # BscScan API требует платный план

logger = get_logger('main')
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def main():
    try:
        init_db()
        ensure_columns()  # ← ДОБАВЬ ЭТУ СТРОКУ
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        return

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(commands.router)
    dp.include_router(onboarding.router)
    dp.include_router(payments.router)
    dp.include_router(topics.router)
    dp.include_router(quiz.router)
    dp.include_router(conversation.router)  # последний — ловит весь текст

    logger.info("🤖 Бот запущен и готов к работе!")
    await bot.delete_webhook(drop_pending_updates=True)

    # Фоновая проверка USDT отключена (BscScan API требует платный план)
    # asyncio.create_task(start_payment_checker(bot))

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Критическая ошибка при работе бота: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())