import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.path.join(os.path.dirname(__file__), "bot.db")

# --- columns cache for users table ---
_USERS_COLUMNS_CACHE = None


def get_users_columns() -> list[str]:
    """
    Возвращает список колонок таблицы users в реальном порядке SQLite.
    Кешируем, чтобы не дергать PRAGMA на каждое сообщение.
    """
    global _USERS_COLUMNS_CACHE
    if _USERS_COLUMNS_CACHE is not None:
        return _USERS_COLUMNS_CACHE

    with _connect_locked() as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = [row[1] for row in cur.fetchall()]  # row[1] = name
        _USERS_COLUMNS_CACHE = cols
        return cols


def user_get(user_row: tuple, column: str, default=None):
    cols = get_users_columns()
    try:
        idx = cols.index(column)
    except ValueError:
        return default
    if idx >= len(user_row):
        return default
    val = user_row[idx]
    return default if val is None else val


# Один общий lock на все операции с БД.
# Важно: SQLite на Windows легко ловит "database is locked", если параллельно
# идут несколько записей/DDL или кто-то держит транзакцию открытой.
_db_lock = threading.RLock()

# Таймаут ожидания разблокировки БД (сек)
_SQLITE_TIMEOUT = float(os.getenv("SQLITE_TIMEOUT", "30"))


def _get_connection() -> sqlite3.Connection:
    # check_same_thread=False безопаснее, если какие-то операции окажутся в других потоках
    # (например, вызовы из фоновых задач/исполнителей).
    conn = sqlite3.connect(
        DB_NAME,
        timeout=_SQLITE_TIMEOUT,
        check_same_thread=False,
    )
    # Практические настройки для конкуренции:
    # - busy_timeout: сколько ждать, если файл залочен
    # - WAL: читатели не блокируют писателей и наоборот (как правило)
    conn.execute("PRAGMA busy_timeout = 10000;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.row_factory = None
    return conn


@contextmanager
def _connect_locked():
    with _db_lock:
        conn = _get_connection()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db():
    with _connect_locked() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                message_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT DEFAULT NULL,
                onboarding_completed INTEGER DEFAULT 0,
                last_active_date TEXT,
                streak_days INTEGER DEFAULT 0,
                referral_code TEXT,
                last_referral_bonus TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                expires_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                payment_method TEXT,
                amount REAL,
                currency TEXT,
                transaction_id TEXT UNIQUE,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inviter_id INTEGER NOT NULL,
                invitee_id INTEGER NOT NULL UNIQUE,
                referral_code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(inviter_id) REFERENCES users(user_id),
                FOREIGN KEY(invitee_id) REFERENCES users(user_id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_transactions (
                tx_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
            """
        )


def create_user(user_id: int, username: str):
    with _connect_locked() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username),
        )


def get_user(user_id: int):
    # Даже чтение делаем через lock: иначе чтение может столкнуться с DDL/WRITE и получить lock.
    with _connect_locked() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cur.fetchone()


def set_user_level(user_id: int, level: str):
    with _connect_locked() as conn:
        conn.execute("UPDATE users SET level = ? WHERE user_id = ?", (level, user_id))


def mark_onboarding_completed(user_id: int):
    with _connect_locked() as conn:
        conn.execute(
            "UPDATE users SET onboarding_completed = 1 WHERE user_id = ?", (user_id,)
        )


def is_onboarding_completed(user_id: int) -> bool:
    user = get_user(user_id)
    return bool(user and user[5])


def increment_message_count(user_id: int, username: str = None):
    with _connect_locked() as conn:
        conn.execute(
            "UPDATE users SET message_count = message_count + 1 WHERE user_id = ?",
            (user_id,),
        )


def update_user_streak(user_id: int, streak: int, last_active_date: str):
    with _connect_locked() as conn:
        conn.execute(
            "UPDATE users SET streak_days = ?, last_active_date = ? WHERE user_id = ?",
            (streak, last_active_date, user_id),
        )


def set_referral_code(user_id: int, referral_code: str):
    with _connect_locked() as conn:
        conn.execute(
            "UPDATE users SET referral_code = ? WHERE user_id = ?",
            (referral_code, user_id),
        )


def get_user_by_referral_code(code: str):
    with _connect_locked() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE referral_code = ?", (code,))
        return cur.fetchone()


def activate_subscription(user_id: int, duration_days: int = 7):
    expires_at = (datetime.now() + timedelta(days=duration_days)).isoformat()
    with _connect_locked() as conn:
        conn.execute(
            """
            INSERT INTO subscriptions (user_id, expires_at)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET expires_at = ?
            """,
            (user_id, expires_at, expires_at),
        )
    return datetime.fromisoformat(expires_at)


def get_subscription(user_id: int):
    with _connect_locked() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM subscriptions WHERE user_id = ?", (user_id,))
        return cur.fetchone()


def has_active_subscription(user_id: int) -> bool:
    sub = get_subscription(user_id)
    if not sub:
        return False
    expires_at = datetime.fromisoformat(sub[1])
    return datetime.now() < expires_at


def add_subscription(user_id: int, expires_at: str):
    """Добавляет или обновляет подписку, продлевая её если новая дата позже текущей."""
    with _connect_locked() as conn:
        conn.execute(
            """
            INSERT INTO subscriptions (user_id, expires_at)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET expires_at =
                CASE WHEN expires_at > ? THEN expires_at ELSE ? END
            """,
            (user_id, expires_at, expires_at, expires_at),
        )


def save_payment(
    user_id: int,
    payment_method: str,
    amount: float,
    currency: str,
    transaction_id: str,
    status: str,
):
    with _connect_locked() as conn:
        conn.execute(
            """
            INSERT INTO payments (user_id, payment_method, amount, currency, transaction_id, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, payment_method, amount, currency, transaction_id, status),
        )


def save_message(user_id: int, role: str, content: str):
    with _connect_locked() as conn:
        conn.execute(
            """
            INSERT INTO conversation_history (user_id, role, content)
            VALUES (?, ?, ?)
            """,
            (user_id, role, content),
        )


def get_conversation_history(user_id: int, limit: int = 10):
    with _connect_locked() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT role, content FROM conversation_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        result = cur.fetchall()
        return result[::-1]


def reset_conversation(user_id: int):
    with _connect_locked() as conn:
        conn.execute("DELETE FROM conversation_history WHERE user_id = ?", (user_id,))


def get_total_users():
    with _connect_locked() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        return cur.fetchone()[0]


def get_active_subscriptions():
    now = datetime.now().isoformat()
    with _connect_locked() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM subscriptions WHERE expires_at > ?", (now,))
        return cur.fetchone()[0]


def can_send_message(user_id: int, username: str = None) -> bool:
    WHITELIST = os.getenv("WHITELIST_USERNAMES", "").split(",")
    FREE_LIMIT = int(os.getenv("FREE_MESSAGE_LIMIT", "25"))

    # VIP
    if username and username in WHITELIST:
        return True

    # Premium
    if has_active_subscription(user_id):
        return True

    user = get_user(user_id)
    if not user:
        return True

    # user[2] = message_count
    messages_used = int(user_get(user, "message_count", 0))

    # messages_count у тебя добавляется через ensure_columns(), поэтому обычно это последний столбец
    # (в /status ты используешь user[10]) :contentReference[oaicite:3]{index=3}
    bonus_messages = int(user_get(user, "messages_count", 0))

    total_limit = FREE_LIMIT + max(bonus_messages, 0)
    print(
        f"[LIMIT] user={user_id} used={messages_used} bonus={bonus_messages} total={total_limit}"
    )
    return messages_used < total_limit


def get_users_by_level() -> dict:
    """Вернёт распределение пользователей по уровням (A1/A2/B1/B2/None)."""
    with _connect_locked() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(level, 'Unknown') AS lvl, COUNT(*) FROM users GROUP BY lvl"
        )
        rows = cur.fetchall()
        return {lvl: cnt for (lvl, cnt) in rows}


def get_average_messages() -> float:
    """Среднее количество использованных сообщений на пользователя."""
    with _connect_locked() as conn:
        cur = conn.cursor()
        cur.execute("SELECT AVG(message_count) FROM users")
        val = cur.fetchone()[0]
        return round(float(val), 1) if val is not None else 0.0


def ensure_columns():
    """
    Проверяет и добавляет недостающие колонки в таблицу users
    Безопасно вызывать при каждом запуске
    """
    with _connect_locked() as conn:
        cur = conn.cursor()

        cur.execute("PRAGMA table_info(users)")
        existing_columns = {row[1] for row in cur.fetchall()}

        required_columns = {
            "level": "TEXT",
            "messages_count": "INTEGER DEFAULT 0",
            "onboarding_completed": "INTEGER DEFAULT 0",
            "referral_code": "TEXT",
            "last_streak_reward": "INTEGER DEFAULT 0",
        }

        for column, ddl in required_columns.items():
            if column not in existing_columns:
                cur.execute(f"ALTER TABLE users ADD COLUMN {column} {ddl}")

        conn.commit()


def get_user_id_by_referral_code(referral_code: str):
    """Вернёт user_id владельца referral_code или None."""
    with _connect_locked() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id FROM users WHERE referral_code = ?", (referral_code,)
        )
        row = cur.fetchone()
        return row[0] if row else None


def add_referral(inviter_id: int, invitee_id: int, referral_code: str) -> bool:
    """
    Записывает факт активации реферального кода.
    True = записали, False = invitee уже активировал раньше (одноразово).
    """
    with _connect_locked() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO referrals (inviter_id, invitee_id, referral_code) VALUES (?, ?, ?)",
                (inviter_id, invitee_id, referral_code),
            )
            conn.commit()
            return True
        except Exception as e:
            # invitee_id уникальный — повторная активация
            if "UNIQUE constraint failed: referrals.invitee_id" in str(e):
                return False
            raise


def add_messages(user_id: int, amount: int):
    """Добавляет пользователю сообщения (бонус, рефералка и т.д.)"""
    with _connect_locked() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET messages_count = messages_count + ? WHERE user_id = ?",
            (amount, user_id),
        )
        conn.commit()


def is_vip_username(username: str) -> bool:
    if not username:
        return False
    # WHITELIST_USERNAMES должен быть в main/config; если он у тебя в другом месте — скажи, я подстрою
    try:
        from config import WHITELIST_USERNAMES
    except Exception:
        return False
    return username in WHITELIST_USERNAMES


def add_premium_days(user_id: int, days: int = 1):
    """Добавляет дни подписки Premium (увеличивает expires_at)."""
    with _connect_locked() as conn:
        cur = conn.cursor()

        cur.execute(
            "SELECT expires_at FROM subscriptions WHERE user_id = ?", (user_id,)
        )
        row = cur.fetchone()

        # В SQLite используем datetime('now', '+N day') напрямую в строке
        if row is None:
            # Создаём новую подписку на N дней с текущего момента
            cur.execute(
                f"INSERT INTO subscriptions (user_id, expires_at) VALUES (?, datetime('now', '+{days} day'))",
                (user_id,),
            )
        else:
            # Если подписка уже есть: продлеваем от max(expires_at, now)
            cur.execute(
                f"""
                UPDATE subscriptions
                SET expires_at =
                    CASE
                        WHEN expires_at > datetime('now') THEN datetime(expires_at, '+{days} day')
                        ELSE datetime('now', '+{days} day')
                    END
                WHERE user_id = ?
                """,
                (user_id,),
            )

        conn.commit()


def get_streak_reward_level(user_id: int) -> int:
    """Возвращает максимальный уровень streak-награды, уже полученный пользователем."""
    user = get_user(user_id)
    if not user:
        return 0
    return int(user_get(user, "last_streak_reward", 0))


def set_streak_reward_level(user_id: int, level: int):
    """Устанавливает уровень последней полученной streak-награды."""
    with _connect_locked() as conn:
        conn.execute(
            "UPDATE users SET last_streak_reward = ? WHERE user_id = ?",
            (level, user_id),
        )


def is_transaction_processed(tx_hash: str) -> bool:
    """Проверяет, была ли транзакция уже обработана."""
    with _connect_locked() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM processed_transactions WHERE tx_hash = ?",
            (tx_hash,),
        )
        return cur.fetchone()[0] > 0


def mark_transaction_processed(tx_hash: str, user_id: int, amount: float):
    """Помечает транзакцию как обработанную."""
    with _connect_locked() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO processed_transactions (tx_hash, user_id, amount)
            VALUES (?, ?, ?)
            """,
            (tx_hash, user_id, amount),
        )
        conn.commit()
