"""
Сервис для автоматической проверки USDT транзакций через BscScan API
"""
import requests
import os
from dotenv import load_dotenv
from logger import get_logger

load_dotenv()

logger = get_logger('bscscan')

BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY")
USDT_WALLET = os.getenv("USDT_WALLET_ADDRESS")

# USDT BEP-20 контракт на BSC
USDT_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"

def check_usdt_transactions(wallet_address: str, start_block: int = 0):
    """
    Проверяет входящие USDT транзакции на указанный кошелек
    
    Args:
        wallet_address: Адрес кошелька для проверки
        start_block: Номер блока с которого начинать проверку
        
    Returns:
        list: Список транзакций [{from, to, value, hash, timestamp}, ...]
    """
    if not BSCSCAN_API_KEY:
        logger.error("BSCSCAN_API_KEY не настроен в .env")
        return []
    
    if not wallet_address:
        logger.warning("Wallet address не указан")
        return []
    
    try:
        # API endpoint для получения BEP-20 транзакций
        url = "https://api.bscscan.com/api"
        
        params = {
            "module": "account",
            "action": "tokentx",
            "contractaddress": USDT_CONTRACT,
            "address": wallet_address,
            "startblock": start_block,
            "endblock": 99999999,
            "page": "1",
            "offset": "100",
            "sort": "desc",
            "apikey": BSCSCAN_API_KEY
        }

        
        logger.info(f"Проверяю транзакции для кошелька {wallet_address[:10]}...")
        
        response = requests.get(url, params=params, timeout=10)

        # Отладка: смотрим что вернул сервер
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response text (first 500 chars): {response.text[:500]}")

        data = response.json()

        
        if data["status"] != "1":
            error_msg = data.get("message", "Unknown error")
            result_msg = data.get("result", "No result")
            
            logger.error(f"❌ BscScan API Error Details:")
            logger.error(f"   Status: {data.get('status')}")
            logger.error(f"   Message: {error_msg}")
            logger.error(f"   Result: {result_msg}")
            logger.error(f"   Full response: {data}")
            
            if "No transactions found" in error_msg:
                logger.info("Транзакций не найдено (это нормально если платежей нет)")
                return []
            
            return []


        
        transactions = data["result"]
        
        # Фильтруем только входящие транзакции
        incoming = [
            {
                "from": tx["from"],
                "to": tx["to"],
                "value": float(tx["value"]) / 1e18,  # Конвертируем из wei в USDT
                "hash": tx["hash"],
                "timestamp": int(tx["timeStamp"]),
                "block": int(tx["blockNumber"])
            }
            for tx in transactions
            if tx["to"].lower() == wallet_address.lower()
        ]
        
        logger.info(f"Найдено {len(incoming)} входящих транзакций")
        return incoming
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка сети при запросе к BscScan: {e}")
        return []
    except Exception as e:
        logger.error(f"Неожиданная ошибка при проверке транзакций: {e}", exc_info=True)
        return []


def find_payment_by_amount(amount: float = 1.5, tolerance: float = 0.01):
    """
    Ищет входящие USDT транзакции с указанной суммой
    
    Args:
        amount: Ожидаемая сумма платежа (по умолчанию 1.5 USDT)
        tolerance: Допустимое отклонение (по умолчанию 0.01)
        
    Returns:
        list: Список подходящих транзакций
    """
    if not USDT_WALLET:
        logger.warning("USDT_WALLET_ADDRESS не настроен")
        return []
    
    transactions = check_usdt_transactions(USDT_WALLET)
    
    # Фильтруем по сумме с учетом погрешности
    matching = [
        tx for tx in transactions
        if abs(tx["value"] - amount) <= tolerance
    ]
    
    if matching:
        logger.info(f"Найдено {len(matching)} транзакций на сумму {amount} USDT")
    
    return matching
