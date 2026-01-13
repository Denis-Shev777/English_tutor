import sqlite3

DB_NAME = "bot.db"

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Проверяем текущую структуру
cursor.execute("PRAGMA table_info(users)")
columns = cursor.fetchall()
print("Текущие колонки:")
for col in columns:
    print(f"  - {col[1]}")

# Проверяем есть ли message_count
has_message_count = any(col[1] == 'message_count' for col in columns)

if not has_message_count:
    print("\n❌ Колонка message_count отсутствует!")
    print("Добавляем колонку...")
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN message_count INTEGER DEFAULT 0")
        conn.commit()
        print("✅ Колонка message_count добавлена!")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
else:
    print("\n✅ Колонка message_count уже есть!")

conn.close()