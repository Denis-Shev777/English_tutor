"""
Фоновая задача для автоматической проверки USDT платежей
"""
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

from logger import get_logger
from services.bscscan_service import find_payment_by_amount
from database import (
    is_transaction_processed,
    mark_transaction_processed,
    activate_subscription,
    save_payment,
    get_user
)

load_dotenv()

logger = get_logger('payment_checker')

USDT_WALLET = os.getenv("USDT_WALLET_ADDRESS")
CHECK_INTERVAL = 5 * 60  # 5 минут в секундах


async def check_pending_payments(bot):
    """
    Проверяет новые USDT транзакции и активирует подписки
    
    Args:
        bot: Экземпляр бота для отправки уведомлений
    """
    if not USDT_WALLET:
        logger.warning("USDT_WALLET_ADDRESS не настроен - автопроверка отключена")
        return
    
    try:
        logger.info("🔍 Проверяю новые USDT транзакции...")
        
        # Ищем транзакции на 1.5 USDT
        transactions = find_payment_by_amount(amount=1.5, tolerance=0.01)
        
        if not transactions:
            logger.info("Новых платежей не найдено")
            return
        
        # Обрабатываем каждую транзакцию
        for tx in transactions:
            tx_hash = tx["hash"]
            
            # Проверяем не обработали ли мы уже эту транзакцию
            if is_transaction_processed(tx_hash):
                continue
            
            logger.info(f"💰 Новый платеж! Hash: {tx_hash[:16]}... | Сумма: {tx['value']} USDT")
            
            # Здесь мы НЕ ЗНАЕМ user_id, так как платеж пришел извне
            # Отправляем уведомление администратору для ручной активации
            
            # Получаем первого пользователя из WHITELIST (это админ)
            from database import WHITELIST_USERNAMES
            if WHITELIST_USERNAMES:
                # Находим user_id админа по username
                from database import get_user_by_username
                
                # Пока просто логируем, активацию делаем через команду
                logger.warning(
                    f"⚠️ ТРЕБУЕТСЯ РУЧНАЯ АКТИВАЦИЯ!\n"
                    f"Получен платеж {tx['value']} USDT\n"
                    f"Hash: {tx_hash}\n"
                    f"От: {tx['from']}\n"
                    f"Время: {datetime.fromtimestamp(tx['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Используйте команду /activate для привязки к пользователю"
                )
                
                # Отмечаем транзакцию как обработанную (чтобы не показывать повторно)
                # user_id=0 означает что платеж получен, но еще не привязан к пользователю
                mark_transaction_processed(tx_hash, user_id=0, amount=tx['value'])
                
    except Exception as e:
        logger.error(f"Ошибка при проверке платежей: {e}", exc_info=True)


async def start_payment_checker(bot):
    """
    Запускает фоновую задачу проверки платежей
    
    Args:
        bot: Экземпляр бота
    """
    logger.info(f"🚀 Запущена автопроверка USDT платежей (каждые {CHECK_INTERVAL // 60} минут)")
    
    while True:
        try:
            await check_pending_payments(bot)
        except Exception as e:
            logger.error(f"Критическая ошибка в payment_checker: {e}", exc_info=True)
        
        # Ждем 5 минут до следующей проверки
        await asyncio.sleep(CHECK_INTERVAL)
