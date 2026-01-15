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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            level TEXT DEFAULT NULL,
            onboarding_completed INTEGER DEFAULT 0,
            referral_code TEXT DEFAULT NULL,
            last_referral_sent TIMESTAMP DEFAULT NULL
        )
    """)

    # Миграция: добавляем новые колонки если их нет
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN level TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass  # Колонка уже существует

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN onboarding_completed INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Колонка уже существует

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN referral_code TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass  # Колонка уже существует

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN last_referral_sent TIMESTAMP DEFAULT NULL")
    except sqlite3.OperationalError:
        pass  # Колонка уже существует
    
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

    # Таблица рефералов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            bonus_given INTEGER DEFAULT 0,
            FOREIGN KEY (referrer_id) REFERENCES users(user_id),
            FOREIGN KEY (referred_id) REFERENCES users(user_id)
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
    import hashlib
    import time

    # Генерируем уникальный реферальный код
    referral_code = hashlib.md5(f"{user_id}{time.time()}".encode()).hexdigest()[:8].upper()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username, message_count, referral_code) VALUES (?, ?, 0, ?)",
            (user_id, username, referral_code)
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

def set_user_level(user_id: int, level: str):
    """Установить уровень пользователя (A1, A2, B1, B2)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET level = ? WHERE user_id = ?",
        (level, user_id)
    )
    conn.commit()
    conn.close()

def get_user_level(user_id: int):
    """Получить уровень пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT level FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def mark_onboarding_completed(user_id: int):
    """Отметить онбординг как завершенный"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET onboarding_completed = 1 WHERE user_id = ?",
        (user_id,)
    )
    conn.commit()
    conn.close()

def is_onboarding_completed(user_id: int) -> bool:
    """Проверить завершен ли онбординг"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT onboarding_completed FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return bool(result[0]) if result else False

def get_referral_code(user_id: int):
    """Получить реферальный код пользователя"""
    import hashlib
    import time

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT referral_code FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    # Если кода нет - генерируем
    if result and not result[0]:
        referral_code = hashlib.md5(f"{user_id}{time.time()}".encode()).hexdigest()[:8].upper()
        cursor.execute("UPDATE users SET referral_code = ? WHERE user_id = ?", (referral_code, user_id))
        conn.commit()
        conn.close()
        return referral_code

    conn.close()
    return result[0] if result else None

def get_level_stats():
    """Получить статистику пользователей по уровням"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            level,
            COUNT(*) as count
        FROM users
        WHERE level IS NOT NULL
        GROUP BY level
        ORDER BY
            CASE level
                WHEN 'A1' THEN 1
                WHEN 'A2' THEN 2
                WHEN 'B1' THEN 3
                WHEN 'B2' THEN 4
                ELSE 5
            END
    """)
    stats = cursor.fetchall()
    conn.close()
    return stats

def add_referral(referrer_id: int, referred_id: int):
    """Добавить реферала"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)",
            (referrer_id, referred_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Ошибка добавления реферала: {e}")
        return False
    finally:
        conn.close()

def get_user_by_referral_code(referral_code: str):
    """Получить пользователя по реферальному коду"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username FROM users WHERE referral_code = ?", (referral_code,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_referral_count(user_id: int):
    """Получить количество рефералов пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def give_referral_bonus(referrer_id: int, referrer_username: str, referred_id: int):
    """
    Начислить бонус за реферала
    - Premium реферер: +1 день подписки ему, +50 сообщений другу
    - VIP реферер: ничего ему (уже безлимит), +50 сообщений другу
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        # Даем новому пользователю +50 сообщений
        bonus_messages = 50
        cursor.execute(
            "UPDATE users SET message_count = CASE WHEN message_count - ? < 0 THEN 0 ELSE message_count - ? END WHERE user_id = ?",
            (bonus_messages, bonus_messages, referred_id)
        )

        # Проверяем статус реферера
        # Если не в whitelist - значит Premium, даем +1 день подписки
        if referrer_username not in WHITELIST_USERNAMES:
            # Получаем текущую подписку
            cursor.execute("SELECT expires_at FROM subscriptions WHERE user_id = ?", (referrer_id,))
            sub = cursor.fetchone()

            if sub:
                # Есть подписка - добавляем 1 день
                current_expires = datetime.fromisoformat(sub[0])
                new_expires = current_expires + timedelta(days=1)
                cursor.execute(
                    "UPDATE subscriptions SET expires_at = ? WHERE user_id = ?",
                    (new_expires.isoformat(), referrer_id)
                )

        # Отмечаем что бонус выдан
        cursor.execute(
            "UPDATE referrals SET bonus_given = 1 WHERE referrer_id = ? AND referred_id = ?",
            (referrer_id, referred_id)
        )

        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Ошибка начисления бонуса: {e}")
        return False
    finally:
        conn.close()

def can_send_referral(user_id: int, username: str):
    """
    Проверить может ли пользователь отправлять реферальную ссылку
    Условия:
    - Должен быть Premium или VIP
    - Не отправлял рефку за последнюю неделю
    """
    # Проверяем что пользователь VIP или Premium
    is_vip = username and username in WHITELIST_USERNAMES
    is_premium = has_active_subscription(user_id)

    if not (is_vip or is_premium):
        return False, "Реферальная программа доступна только Premium и VIP пользователям"

    # Проверяем когда последний раз отправлял
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT last_referral_sent FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result and result[0]:
        last_sent = datetime.fromisoformat(result[0])
        week_ago = datetime.now() - timedelta(days=7)

        if last_sent > week_ago:
            days_left = 7 - (datetime.now() - last_sent).days
            return False, f"Следующую рефку можно отправить через {days_left} дней"

    return True, "OK"

def update_last_referral_sent(user_id: int):
    """Обновить время последней отправки реферальной ссылки"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET last_referral_sent = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Ошибка обновления last_referral_sent: {e}")
        return False
    finally:
        conn.close()

# Инициализация при импорте
init_db()