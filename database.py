import sqlite3
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

DB_NAME = "bot.db"

# Белый список пользователей (безлимит) - загружается из .env
# Формат в .env: WHITELIST_USERNAMES=user1,user2,user3 (БЕЗ @)
WHITELIST_USERNAMES = os.getenv("WHITELIST_USERNAMES", "").split(",") if os.getenv("WHITELIST_USERNAMES") else []
WHITELIST_USERNAMES = [username.strip() for username in WHITELIST_USERNAMES if username.strip()]

# Настройки бота из .env
FREE_MESSAGE_LIMIT = int(os.getenv("FREE_MESSAGE_LIMIT", "25"))
MIN_MESSAGE_COOLDOWN = int(os.getenv("MIN_MESSAGE_COOLDOWN", "3"))

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            message_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица подписок
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # Таблица истории разговоров
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # Таблица платежей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            payment_method TEXT,
            amount REAL,
            currency TEXT,
            transaction_id TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def get_user(user_id: int):
    """Получить пользователя по ID"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(user_id: int, username: str):
    """Создать нового пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username, message_count) VALUES (?, ?, 0)",
            (user_id, username)
        )
        conn.commit()
    except Exception as e:
        print(f"❌ Ошибка создания пользователя: {e}")
    finally:
        conn.close()

def increment_message_count(user_id: int, username: str = None):
    """Увеличить счётчик сообщений (если не в белом списке)"""
    if username and username in WHITELIST_USERNAMES:
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET message_count = message_count + 1 WHERE user_id = ?",
        (user_id,)
    )
    conn.commit()
    conn.close()

def can_send_message(user_id: int, username: str = None) -> bool:
    """Проверяет может ли пользователь отправить сообщение"""
    
    # Проверяем белый список по username
    if username and username in WHITELIST_USERNAMES:
        return True
    
    # Проверяем активную подписку
    if has_active_subscription(user_id):
        return True
    
    # Проверяем лимит сообщений
    user = get_user(user_id)
    if user and user[2] < FREE_MESSAGE_LIMIT:
        return True
    
    return False

def get_conversation_history(user_id: int, limit: int = 8):
    """
    Получить последние N сообщений из истории разговора

    Args:
        user_id: ID пользователя
        limit: Максимальное количество сообщений (по умолчанию 8)

    Returns:
        list: Список кортежей (role, content)
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT role, content
        FROM conversation_history
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (user_id, limit)
    )
    history = cursor.fetchall()
    conn.close()
    # Возвращаем в правильном порядке (старые сообщения сначала)
    return list(reversed(history))

def save_message(user_id: int, role: str, content: str):
    """Сохранить сообщение в историю"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversation_history (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content)
    )
    conn.commit()
    conn.close()

def reset_conversation(user_id: int):
    """Сбросить историю разговора пользователя"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversation_history WHERE user_id = ?", (user_id,))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        print(f"✅ Удалено {deleted_count} сообщений для user_id={user_id}")
        return True
    except Exception as e:
        print(f"❌ Ошибка при сбросе истории: {e}")
        return False

def activate_subscription(user_id: int, duration_days: int = 7):
    """Активировать подписку"""
    expires = datetime.now() + timedelta(days=duration_days)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO subscriptions (user_id, expires_at) VALUES (?, ?)",
        (user_id, expires.isoformat())
    )
    conn.commit()
    conn.close()
    return expires

def get_subscription(user_id: int):
    """Получить подписку пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, expires_at FROM subscriptions WHERE user_id = ?", (user_id,))
    subscription = cursor.fetchone()
    conn.close()
    return subscription

def has_active_subscription(user_id: int) -> bool:
    """Проверить активна ли подписка"""
    subscription = get_subscription(user_id)
    if not subscription:
        return False
    
    expires = datetime.fromisoformat(subscription[1])
    return expires > datetime.now()

def save_payment(user_id: int, payment_method: str, amount: float, 
                currency: str, transaction_id: str, status: str):
    """Сохранить информацию о платеже"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO payments (user_id, payment_method, amount, currency, transaction_id, status) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, payment_method, amount, currency, transaction_id, status)
    )
    conn.commit()
    conn.close()

def get_total_users():
    """Получить общее количество пользователей"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_active_subscriptions():
    """Получить количество активных подписок"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE expires_at > ?", (now,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

# Инициализация при импорте
init_db()