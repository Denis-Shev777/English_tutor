import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Google Cloud credentials
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Pexels API
PEXELS_KEY = os.getenv("PEXELS_API_KEY")

# Unsplash API (резервный)
UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

# USDT Wallet
USDT_WALLET = os.getenv("USDT_WALLET_ADDRESS")

# Проверка токена
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env файле!")

print("✅ Конфигурация загружена")
print(f"📱 Bot Token: {BOT_TOKEN[:10]}...{BOT_TOKEN[-10:]}")

if PEXELS_KEY:
    print(f"📸 Pexels Key: {PEXELS_KEY[:10]}...")

if UNSPLASH_KEY:
    print(f"🎨 Unsplash Key: {UNSPLASH_KEY[:10]}... (резервный)")