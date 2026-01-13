from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_user, create_user, clear_conversation_history, is_whitelisted

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Создаём пользователя если нужно
    user = get_user(user_id)
    if not user:
        create_user(user_id, username)
    
    # Проверяем white list
    if is_whitelisted(username):
        greeting = (
            "👑 **Hi Admin!**\n\n"
            "You have **unlimited access** to the bot.\n\n"
        )
    else:
        greeting = (
            "👋 **Hi! I'm your English Speaking Bot!**\n\n"
            "🎤 Send me voice messages (or text) and I'll help you practice English.\n"
            "I'll correct your mistakes and keep the conversation going.\n\n"
            "🎁 You have **25 free messages** to try!\n\n"
        )
    
    await message.answer(
        greeting +
        "**Commands:**\n"
        "/start - Start over\n"
        "/status - Check your message count\n"
        "/reset - Clear conversation history\n"
        "/help - Get help\n\n"
        "Let's start! Say something in English 🗣",
        parse_mode="Markdown"
    )

@router.message(Command("status"))
async def cmd_status(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        await message.answer("Use /start first!")
        return
    
    username = user[1]
    messages_used = user[2]
    subscription_active = user[3]
    
    # White list пользователи
    if is_whitelisted(username):
        await message.answer(
            "👑 **Admin Status:**\n\n"
            "You have **unlimited messages**!\n"
            f"Messages used: {messages_used} (no limit) 🎉",
            parse_mode="Markdown"
        )
        return
    
    # Обычные пользователи
    if subscription_active:
        await message.answer(
            "✅ **Your subscription is active!**\n"
            "You have unlimited messages 🎉",
            parse_mode="Markdown"
        )
    else:
        messages_left = 25 - messages_used
        await message.answer(
            f"📊 **Your Status:**\n\n"
            f"Messages used: {messages_used}/25\n"
            f"Messages left: {messages_left}\n\n"
            f"{'⚠️ Almost done! Get a subscription with /buy' if messages_left <= 5 else ''}",
            parse_mode="Markdown"
        )

@router.message(Command("reset"))
async def cmd_reset(message: Message):
    user_id = message.from_user.id
    clear_conversation_history(user_id)
    await message.answer(
        "🔄 Conversation reset! Let's start fresh.\n"
        "What would you like to talk about?"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ **How to use this bot:**\n\n"
        "1️⃣ Send voice messages in English (recommended)\n"
        "2️⃣ Or type text messages\n"
        "3️⃣ I'll correct your mistakes and explain them\n"
        "4️⃣ Ask me to show pictures: 'Show me a photo of...'\n"
        "5️⃣ Ask about words: 'What does ... mean?'\n\n"
        "🎁 Free trial: 25 messages\n"
        "💎 Subscription: unlimited access\n\n"
        "Questions? Just ask me!",
        parse_mode="Markdown"
    )