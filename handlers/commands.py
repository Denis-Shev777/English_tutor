from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (
    get_user,
    create_user,
    reset_conversation,
    get_subscription,
    has_active_subscription,
    WHITELIST_USERNAMES,
    get_total_users,
    get_active_subscriptions,
    is_onboarding_completed
)

from handlers.keyboards import get_main_menu, get_buy_menu

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Создаём пользователя если не существует
    user = get_user(user_id)
    
    if not user:
        create_user(user_id, username)
    
    # Проверяем онбординг
    if not is_onboarding_completed(user_id):
        # Запускаем онбординг для новых пользователей
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать!", callback_data="start_onboarding")]
        ])
        
        await message.answer(
            f"Привет, {username}! 👋\n\n"
            "Я твой помощник для практики английского! 🎓\n\n"
            "**Что я умею:**\n"
            "• Практика разговорной речи (голос и текст)\n"
            "• Мягкие исправления ошибок\n"
            "• Помощь с грамматикой и словами\n"
            "• Адаптация под твой уровень\n\n"
            "Давай начнем с определения твоего уровня!",
            reply_markup=keyboard
        )
        return
    
    # Обычное приветствие для пользователей с онбордингом
    await message.answer(
        f"Привет, {username}!\n\n"
        "Я твой помощник для практики английского! 🎓\n\n"
        "**Как использовать:**\n"
        "• Отправляй голосовые или текстовые сообщения на английском\n"
        "• Я помогу тебе практиковать разговорную речь\n"
        "• Мягко исправлю твои ошибки\n"
        "• Спрашивай о словах, грамматике или просто общайся!\n\n"
        "**Бесплатно:** 25 сообщений\n"
        "**Premium:** Безлимитный доступ всего за 100 Stars/неделю\n\n"
        "Используй кнопки ниже для быстрого доступа! ⬇️",
        reply_markup=get_main_menu(user_id, username)
    )

@router.message(F.text == "📊 Мой статус")
@router.message(Command("status"))
async def cmd_status(message: Message):
    """Команда /status или кнопка"""
    user_id = message.from_user.id
    username = message.from_user.username
    user = get_user(user_id)
    
    if not user:
        await message.answer("❌ User not found. Please use /start first.")
        return
    
    # Белый список по username
    if username and username in WHITELIST_USERNAMES:
        await message.answer(
            "⭐ **VIP Status**\n\n"
            "You have unlimited access!\n"
            "Messages used: ∞\n"
            "Subscription: Lifetime Premium 💎",
            reply_markup=get_main_menu(user_id, username)
        )
        return
    
    # Проверяем подписку
    subscription = get_subscription(user_id)
    
    if has_active_subscription(user_id) and subscription:
        expires = datetime.fromisoformat(subscription[1])
        days_left = (expires - datetime.now()).days
        
        await message.answer(
            f"✅ **Premium Active**\n\n"
            f"Status: Premium 💎\n"
            f"Expires: {expires.strftime('%Y-%m-%d %H:%M')}\n"
            f"Days left: {days_left}\n\n"
            f"Enjoy unlimited practice!",
            reply_markup=get_main_menu(user_id, username)
        )
    else:
        messages_used = user[2]
        messages_left = 25 - messages_used
        
        if messages_left > 0:
            await message.answer(
                f"📊 **Free Tier Status**\n\n"
                f"Messages used: {messages_used}/25\n"
                f"Messages left: {messages_left}\n\n"
                f"Want unlimited access?\n"
                f"Get premium for just **100 Stars/week**!\n\n"
                f"Press button below to upgrade! ⬇️",
                reply_markup=get_main_menu(user_id, username)
            )
        else:
            await message.answer(
                f"🚫 **Free messages exhausted**\n\n"
                f"You've used all 25 free messages.\n\n"
                f"Get premium access:\n"
                f"⭐ **100 Stars** - 1 week\n"
                f"💵 **1.5 USDT (BEP-20)** - 1 week\n\n"
                f"Press button below to continue! ⬇️",
                reply_markup=get_main_menu(user_id, username)
            )

@router.message(F.text == "💎 Купить Premium")
@router.message(F.text == "💎 Продлить Premium")
@router.message(Command("buy"))
async def cmd_buy(message: Message):
    """Команда /buy или кнопка"""
    await message.answer(
        "💎 **Получи Premium доступ!**\n\n"
        "**Что входит:**\n"
        "✅ Безлимитные сообщения\n"
        "✅ Голосовые + текстовые исправления\n"
        "✅ Разговорная практика\n"
        "✅ Доступ 24/7\n\n"
        "**Цены:**\n"
        "⭐ **100 Stars** - 1 неделя (~179 руб)\n"
        "💵 **1.5 USDT (BEP-20)** - 1 неделя\n\n"
        "Выбери способ оплаты:",
        reply_markup=get_buy_menu()
    )

@router.message(F.text == "🧠 Очистить память")  # ← ИЗМЕНИЛИ
@router.message(Command("reset"))
async def cmd_reset(message: Message):
    """Команда /reset или кнопка"""
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Сбрасываем историю
    reset_conversation(user_id)
    
    await message.answer(
        "🧠 **Память очищена!**\n\n"
        "Я забыл нашу переписку и не помню что мы обсуждали.\n"
        "Давай начнём разговор заново! 🎤\n\n"
        "💡 Сообщения в чате остаются видимыми, но я их больше не помню.",
        reply_markup=get_main_menu(user_id, username)
    )

@router.message(F.text == "❓ Помощь")
@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help или кнопка"""
    user_id = message.from_user.id
    username = message.from_user.username
    await message.answer(
        "📚 **Available commands:**\n\n"
        "📊 Мой статус - Check subscription\n"
        "💎 Купить Premium - Get premium access\n"
        "🧠 Очистить память - Bot forgets conversation\n"  # ← ИЗМЕНИЛИ
        "❓ Помощь - Show this help\n\n"
        "**How it works:**\n"
        "1. Send voice or text in English\n"
        "2. I'll respond with corrections and voice\n"
        "3. Practice naturally and improve!\n\n"
        "Need help? Contact @Den_Shev_007",
        reply_markup=get_main_menu(user_id, username)
    )

@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """Показать главное меню"""
    user_id = message.from_user.id
    username = message.from_user.username
    await message.answer(
        "🏠 **Главное меню**\n\n"
        "Используй кнопки ниже для навигации ⬇️",
        reply_markup=get_main_menu(user_id, username)
    )

# ADMIN КОМАНДЫ
@router.message(F.text == "📈 Статистика")
@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Статистика (только для админов)"""
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Проверяем что админ
    if username not in WHITELIST_USERNAMES:
        return
    
    total_users = get_total_users()
    active_subs = get_active_subscriptions()
    
    conversion = (active_subs/total_users*100) if total_users > 0 else 0
    
    await message.answer(
        f"📊 **Bot Statistics**\n\n"
        f"👥 Total users: {total_users}\n"
        f"💎 Active subscriptions: {active_subs}\n"
        f"📈 Conversion: {conversion:.1f}%",
        reply_markup=get_main_menu(user_id, username)
    )