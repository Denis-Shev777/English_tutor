from aiogram import Router, F
from aiogram.types import Message, Voice, FSInputFile
from aiogram.enums import ChatAction
import sys
import os
import asyncio
import random
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (
    get_conversation_history,
    save_message,
    increment_message_count,
    get_user,
    create_user,
    can_send_message,
    WHITELIST_USERNAMES,
    FREE_MESSAGE_LIMIT,
    is_onboarding_completed,
    get_user_level
)

from services.ollama_service import get_ollama_response
from services.whisper_service import transcribe_audio
from services.tts_service import text_to_speech
from handlers.keyboards import get_main_menu

router = Router()

async def process_user_message(message: Message, user_text: str):
    """
    Общая функция обработки сообщения (текст или распознанная речь)
    """
    user_id = message.from_user.id
    username = message.from_user.username
    bot = message.bot
    
    # ПРОВЕРЯЕМ ЛИМИТ СООБЩЕНИЙ ПЕРЕД ОБРАБОТКОЙ
    if not can_send_message(user_id, username):
        await bot.send_message(
            user_id,
            "Free messages exhausted\n\n"
            "You've used all 25 free messages.\n\n"
            "Get premium access:\n"
            "100 Stars - 1 week\n"
            "1.5 USDT (BEP-20) - 1 week\n\n"
            "Press /buy to continue practicing!",
            reply_markup=get_main_menu(user_id, username)
        )
        return
    
    # Получаем историю разговора
    history = get_conversation_history(user_id)
    
    # Показываем "печатает..."
    await bot.send_chat_action(user_id, ChatAction.TYPING)
    
    # Случайная задержка (имитация размышления)
    await asyncio.sleep(random.uniform(1.5, 3.0))
    
    # Получаем ответ от LLaMA
    bot_response = get_ollama_response(user_text, history)
    
    # Сохраняем в историю
    save_message(user_id, "user", user_text)
    save_message(user_id, "assistant", bot_response)
    
    # Увеличиваем счётчик (ТОЛЬКО если не в белом списке!)
    increment_message_count(user_id, username)
    
    # РАЗДЕЛЯЕМ НА АНГЛИЙСКУЮ И РУССКУЮ ЧАСТИ
    if "---" in bot_response:
        # Есть русский перевод - разделяем
        parts = bot_response.split("---", 1)
        english_part = parts[0].strip()
        full_text = bot_response
    else:
        # Нет перевода - весь ответ на английском
        english_part = bot_response
        full_text = bot_response
    
    # Небольшая задержка перед генерацией голоса
    await asyncio.sleep(random.uniform(0.5, 1.0))
    
    # Показываем "записывает голос..."
    await bot.send_chat_action(user_id, ChatAction.RECORD_VOICE)
    
    # Генерируем голосовой ответ ТОЛЬКО ДЛЯ АНГЛИЙСКОЙ ЧАСТИ
    try:
        # Случайная задержка (имитация записи)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        
        # Создаём аудио ТОЛЬКО из английской части
        audio_path = text_to_speech(english_part)
        
        if audio_path:
            # Отправляем голосовое сообщение
            audio_file = FSInputFile(audio_path)
            await message.answer_voice(audio_file)
            
            # Небольшая задержка перед текстом
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # Отправляем ВЕСЬ текст (английский + русский)
            await message.answer(full_text, reply_markup=get_main_menu(user_id, username))
            
            # Удаляем временный файл
            try:
                os.remove(audio_path)
            except:
                pass
        else:
            # Если TTS не сработал - отправляем только текст
            await message.answer(full_text, reply_markup=get_main_menu(user_id, username))
            
    except Exception as e:
        print(f"Error generating voice: {e}")
        await message.answer(full_text, reply_markup=get_main_menu(user_id, username))
    
    # Показываем статус если мало сообщений (НЕ для белого списка!)
    if not (username and username in WHITELIST_USERNAMES):
        user = get_user(user_id)
        if user:
            messages_left = 25 - user[2]
            if 0 < messages_left <= 5:
                await message.answer(
                    f"You have {messages_left} free messages left.\n"
                    f"Press button below to get unlimited access!",
                    reply_markup=get_main_menu(user_id, username)
                )

@router.message(F.voice)
async def handle_voice_message(message: Message):
    """Обработка ГОЛОСОВЫХ сообщений"""
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Проверяем/создаём пользователя
    user = get_user(user_id)
    if not user:
        create_user(user_id, username or message.from_user.first_name)
    
    # Проверяем онбординг
    if not is_onboarding_completed(user_id):
        await message.answer(
            "Please complete the onboarding first! Use /start to begin.",
            reply_markup=get_main_menu(user_id, username)
        )
        return
    
    # ПРОВЕРЯЕМ ЛИМИТЫ С USERNAME
    if not can_send_message(user_id, username):
        await message.answer(
            "You've used all your free messages!\n\n"
            "Get a subscription to continue practicing English\n\n"
            "Press button below to see prices!",
            reply_markup=get_main_menu(user_id, username)
        )
        return
    
    # Показываем "печатает..." пока обрабатываем
    await message.bot.send_chat_action(user_id, ChatAction.TYPING)
    
    try:
        voice = message.voice
        file = await message.bot.get_file(voice.file_id)
        
        # Создаём временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_file:
            temp_path = temp_file.name
            await message.bot.download_file(file.file_path, temp_path)
        
        # Распознаём речь через Whisper
        user_text = transcribe_audio(temp_path)
        
        # Удаляем временный файл
        try:
            os.remove(temp_path)
        except:
            pass
        
        if not user_text:
            await message.answer(
                "Sorry, I couldn't understand that. Could you try again?\n"
                "Make sure you're speaking clearly in English.",
                reply_markup=get_main_menu(user_id, username)
            )
            return
        
        # Показываем что услышали
        await message.answer(f"You said: \"{user_text}\"")
        
        # Небольшая задержка перед обработкой
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        # Обрабатываем как обычное сообщение
        await process_user_message(message, user_text)
        
    except Exception as e:
        print(f"Error processing voice: {e}")
        import traceback
        traceback.print_exc()
        await message.answer(
            "Sorry, there was an error processing your voice message. "
            "Please try again or send a text message.",
            reply_markup=get_main_menu(user_id, username)
        )

@router.message(F.text)
async def handle_text_message(message: Message):
    """Обработка ТЕКСТОВЫХ сообщений"""
    user_id = message.from_user.id
    username = message.from_user.username
    user_text = message.text
    
    print(f"\n📨 === ПОЛУЧЕНО СООБЩЕНИЕ ===")
    print(f"User ID: {user_id}")
    print(f"Username: {username}")
    print(f"Текст: {user_text}")
    
    # Игнорируем команды и кнопки
    if user_text.startswith('/') or user_text in ["📊 Мой статус", "💎 Купить Premium", "💎 Продлить Premium", "🧠 Очистить память", "❓ Помощь", "📈 Статистика"]:
        print("Это команда или кнопка - игнорируем")
        return
    
    # Проверяем/создаём пользователя
    print(f"Проверяю пользователя в базе...")
    user = get_user(user_id)
    
    if not user:
        print(f"Пользователь не найден! Создаю...")
        create_user(user_id, username or message.from_user.first_name)
        user = get_user(user_id)
        print(f"Пользователь создан: {user}")
    else:
        print(f"Пользователь найден: {user}")
    
    # Проверяем онбординг
    if not is_onboarding_completed(user_id):
        await message.answer(
            "Please complete the onboarding first! Use /start to begin.",
            reply_markup=get_main_menu(user_id, username)
        )
        return
    
    # ПРОВЕРЯЕМ ЛИМИТЫ С USERNAME
    print(f"Проверяю лимиты...")
    can_send = can_send_message(user_id, username)
    print(f"Результат can_send_message: {can_send}")
    
    if not can_send:
        print(f"Лимит исчерпан!")
        await message.answer(
            "You've used all your free messages!\n\n"
            "Get a subscription to continue practicing English\n\n"
            "Press button below to see prices!",
            reply_markup=get_main_menu(user_id, username)
        )
        return
    
    # Обрабатываем сообщение
    await process_user_message(message, user_text)
