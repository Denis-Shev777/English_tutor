from aiogram import Router, F
from aiogram.types import Message, Voice, FSInputFile, CallbackQuery
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
    ВАЖНО: Проверка лимитов должна быть выполнена ДО вызова этой функции!
    """
    user_id = message.from_user.id
    username = message.from_user.username
    bot = message.bot

    # Получаем уровень пользователя
    user_level = get_user_level(user_id)

    # Получаем историю разговора (последние 8 сообщений для контекста)
    history = get_conversation_history(user_id, limit=8)

    # Показываем "печатает..."
    await bot.send_chat_action(user_id, ChatAction.TYPING)

    # Случайная задержка (имитация размышления)
    await asyncio.sleep(random.uniform(1.5, 3.0))

    # Получаем ответ от LLaMA (теперь dict!)
    response_data = get_ollama_response(user_text, history, user_level)

    # Сохраняем в историю (сохраняем только reply для истории)
    save_message(user_id, "user", user_text)
    save_message(user_id, "assistant", response_data["reply"])

    # Увеличиваем счётчик (ТОЛЬКО если не в белом списке!)
    increment_message_count(user_id, username)

    # Формируем текст для отображения
    text_parts = []

    # Основной ответ
    text_parts.append(response_data["reply"])

    # Добавляем вопрос если есть
    if response_data.get("question"):
        text_parts.append(f"\n{response_data['question']}")

    # Добавляем исправление если есть
    if response_data.get("correction"):
        text_parts.append(f"\n\n✏️ Correct: {response_data['correction']}")

    # Добавляем подсказку если есть
    if response_data.get("tip"):
        text_parts.append(f"\n💡 {response_data['tip']}")

    full_text = "".join(text_parts)

    # Для TTS используем reply + question (без corrections и tips с эмодзи)
    tts_parts = [response_data["reply"]]
    if response_data.get("question"):
        tts_parts.append(" " + response_data["question"])
    english_part = "".join(tts_parts)

    # Создаем inline кнопки из quick_replies
    keyboard = None
    if response_data.get("quick_replies") and len(response_data["quick_replies"]) > 0:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        for idx, reply_text in enumerate(response_data["quick_replies"][:4]):  # Максимум 4 кнопки
            # Обрезаем текст до 30 символов для безопасности
            button_text = reply_text[:30]
            # Используем первые 40 символов для callback_data
            callback_data = f"qr_{reply_text[:40]}"
            buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

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

            # Отправляем текст с кнопками (если есть)
            await message.answer(full_text, reply_markup=keyboard or get_main_menu(user_id, username))

            # Удаляем временный файл
            try:
                os.remove(audio_path)
            except:
                pass
        else:
            # Если TTS не сработал - отправляем только текст
            await message.answer(full_text, reply_markup=keyboard or get_main_menu(user_id, username))

    except Exception as e:
        print(f"Error generating voice: {e}")
        await message.answer(full_text, reply_markup=keyboard or get_main_menu(user_id, username))

    # Показываем статус если мало сообщений (НЕ для белого списка!)
    if not (username and username in WHITELIST_USERNAMES):
        user = get_user(user_id)
        if user:
            messages_left = FREE_MESSAGE_LIMIT - user[2]
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
        # Это команда или кнопка - игнорируем
        return
    
    # Проверяем/создаём пользователя
    user = get_user(user_id)
    
    if not user:
        create_user(user_id, username or message.from_user.first_name)

    # ПРОВЕРЯЕМ ЛИМИТЫ С USERNAME
    if not can_send_message(user_id, username):
        await message.answer(
            "You've used all your free messages!\n\n"
            "Get a subscription to continue practicing English\n\n"
            "Press button below to see prices!",
            reply_markup=get_main_menu(user_id, username)
        )
        return
    # Обрабатываем сообщение
    await process_user_message(message, user_text)
@router.callback_query(F.data.startswith("qr_"))
async def handle_quick_reply(callback: CallbackQuery):
    """Обработка нажатия на quick_reply кнопку"""
    await callback.answer()
    
    # Извлекаем текст из callback_data (убираем префикс "qr_")
    reply_text = callback.data[3:]
    
    # Удаляем клавиатуру с кнопками
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass
    
    # Создаем "фейковое" сообщение от пользователя с этим текстом
    # Показываем что пользователь выбрал
    await callback.message.answer(f"You: {reply_text}")
    
    # Обрабатываем как обычное сообщение
    await process_user_message(callback.message, reply_text)
