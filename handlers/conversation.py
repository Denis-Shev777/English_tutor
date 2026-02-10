from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.enums import ChatAction
import sys
import os
import re
import json
import ast
import asyncio
import random
import tempfile
from time import time
from datetime import date, timedelta
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (
    get_conversation_history,
    save_message,
    increment_message_count,
    get_user,
    create_user,
    can_send_message,
    is_onboarding_completed,
    update_user_streak,
    user_get,
    has_active_subscription,
    get_streak_reward_level,
    set_streak_reward_level,
    add_messages,
    add_premium_days,
)

# Streak-награды: {дней: (описание, бонус сообщений, бонус дней премиум)}
STREAK_MILESTONES = {
    3: ("🎁 +5 бесплатных сообщений!", 5, 0),
    7: ("🎁 +10 бесплатных сообщений!", 10, 0),
    14: ("🎁 +20 бесплатных сообщений!", 20, 0),
    30: ("⭐ +1 день Premium подписки!", 0, 1),
}

from services.ollama_service import get_ollama_response
from services.whisper_service import transcribe_audio
from services.tts_service import text_to_speech
from handlers.keyboards import get_main_menu

from dotenv import load_dotenv

load_dotenv()
WHITELIST_USERNAMES = os.getenv("WHITELIST_USERNAMES", "").split(",")

from logger import get_logger

logger = get_logger("conversation")

router = Router()
_last_message_time = {}
RATE_LIMIT_SECONDS = 3
SUGGESTIONS_CACHE: dict[int, dict[str, str]] = {}


# phrases = [p.strip() for p in phrases if isinstance(p, str) and p.strip()]


def build_suggestions_inline(phrases: list[str]) -> InlineKeyboardMarkup:
    keyboard = []
    for phrase in phrases[:4]:
        # Ограничиваем длину callback_data (макс. 64 байта)
        safe_phrase = phrase[:50].replace(":", "").strip()
        if safe_phrase:
            keyboard.append(
                [InlineKeyboardButton(text=phrase, callback_data=f"sugg:{safe_phrase}")]
            )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def extract_english_for_tts(text: str) -> str:
    """
    Оставляем для TTS только английские символы и базовую пунктуацию.
    Убираем кириллицу, чтобы Coqui не читал русские слова по буквам.
    """
    if not text:
        return ""

    allowed = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?;:'\"-()[]\n"
    )
    filtered = "".join(ch for ch in text if ch in allowed)

    # После удаления кириллицы часто остаются " - " и одиночные знаки,
    # которые TTS произносит как "dash/dot". Чистим их.
    filtered = re.sub(r"\s*-\s*", " ", filtered)
    filtered = re.sub(r"\s*:\s*", " ", filtered)
    filtered = re.sub(r"\s*\.\s*\.\s*\.\s*", ". ", filtered)

    # Убираем пустые строки/двойные пробелы
    lines = [ln.strip() for ln in filtered.splitlines() if ln.strip()]
    clean_lines = []
    for ln in lines:
        # Линии из одной пунктуации не нужны для озвучки.
        if re.fullmatch(r"[\W_]+", ln):
            continue
        # Убираем пунктуацию в начале/конце строки, оставляя внутреннюю.
        ln = re.sub(r"^[\s\.,;:!?\-]+", "", ln)
        ln = re.sub(r"[\s\.,;:!?\-]+$", "", ln)
        if ln:
            clean_lines.append(ln)

    result = "\n".join(clean_lines)
    while "  " in result:
        result = result.replace("  ", " ")
    return result.strip()


async def process_user_message(message: Message, user_text: str, from_user=None):
    """from_user — передавать callback.from_user при вызове из callback-хендлеров."""
    if from_user:
        user_id = from_user.id
        username = from_user.username
    else:
        user_id = message.from_user.id
        username = message.from_user.username
    bot = message.bot

    history = get_conversation_history(user_id)
    await bot.send_chat_action(user_id, ChatAction.TYPING)
    await asyncio.sleep(random.uniform(1.5, 3.0))

    # --- Получаем уровень пользователя ---
    user_level = "A1"
    user = get_user(user_id)
    if user and len(user) > 4 and user[4]:
        user_level = user[4]

    # --- Запрос к LLM (теперь возвращает dict) ---
    response_data = get_ollama_response(user_text, history, level=user_level or "A1")

    # --- Извлекаем компоненты ---
    reply = response_data.get("reply", "").strip()
    question = response_data.get("question")
    quick_replies = response_data.get("quick_replies", [])
    correction = response_data.get("correction")
    tip = response_data.get("tip")

    # --- Формируем финальный текст ---
    parts = []
    if correction:
        parts.append(f"✅ {correction}")
    if reply:
        parts.append(reply)
    if question:
        parts.append(question)
    full_text = "\n".join(parts).strip()

    # --- Сохраняем в историю ---
    save_message(user_id, "user", user_text)
    save_message(user_id, "assistant", full_text)
    increment_message_count(user_id, username)

    # --- STREAK ---
    user_data = user
    if user_data and len(user_data) >= 8:
        last_active = user_data[6]
        current_streak = user_data[7] or 0
        today = date.today()
        today_str = today.isoformat()
        if last_active == today_str:
            new_streak = current_streak
        elif last_active == (today - timedelta(days=1)).isoformat():
            new_streak = current_streak + 1
        else:
            new_streak = 1
        update_user_streak(user_id, new_streak, today_str)

    # --- TTS: только английский текст ---
    tts_text = extract_english_for_tts(reply + (" " + question if question else ""))

    # --- Отправляем голос (если есть) ---
    audio_path = None
    if tts_text:
        try:
            await bot.send_chat_action(user_id, ChatAction.RECORD_VOICE)
            await asyncio.sleep(random.uniform(2.0, 4.0))
            audio_path = text_to_speech(tts_text)
            if audio_path:
                audio_file = FSInputFile(audio_path)
                await message.answer_voice(audio_file)
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Error generating voice: {e}", exc_info=True)

    # --- Готовим клавиатуру для quick replies (только A1/A2 и если есть вопрос) ---
    quick_reply_kb = None
    if user_level in ["A1", "A2"] and question and quick_replies:
        # Очищаем и ограничиваем
        clean_phrases = []
        for p in quick_replies[:4]:
            if isinstance(p, str):
                t = p.strip()
                if t and len(t) <= 35:
                    clean_phrases.append(t)
        if clean_phrases:
            SUGGESTIONS_CACHE[message.message_id] = {
                str(i): clean_phrases[i] for i in range(len(clean_phrases))
            }
            quick_reply_kb = build_suggestions_inline(clean_phrases)

    # --- Отправляем основной текст с клавиатурой (если есть) ---
    main_kb = get_main_menu(user_id, username)
    final_kb = quick_reply_kb or main_kb

    await message.answer(full_text, reply_markup=final_kb)

    # --- Удаляем временный аудиофайл ---
    if audio_path:
        try:
            os.remove(audio_path)
        except:
            pass

    # --- Предупреждение о лимите (FREE) ---
    if not (username and username in WHITELIST_USERNAMES) and user_data:
        if not has_active_subscription(user_id):
            FREE_LIMIT = int(os.getenv("FREE_MESSAGE_LIMIT", "25"))
            used = int(user_get(user_data, "message_count", 0))
            bonus = int(user_get(user_data, "messages_count", 0))
            total = FREE_LIMIT + max(bonus, 0)
            messages_left = total - used
            if 0 < messages_left <= 5:
                await message.answer(
                    f"You have {messages_left} free messages left.\n"
                    f"Press button below to get unlimited access!",
                    reply_markup=main_kb,
                )

    # --- Streak уведомление + награды ---
    if "last_active" in locals() and last_active != today_str:
        days = new_streak
        if days % 10 == 1 and days % 100 != 11:
            word = "день"
        elif 2 <= days % 10 <= 4 and not (12 <= days % 100 <= 14):
            word = "дня"
        else:
            word = "дней"

        # Проверяем streak-награды
        last_reward = get_streak_reward_level(user_id)
        reward_text = ""
        for milestone, (desc, bonus_msgs, bonus_days) in sorted(STREAK_MILESTONES.items()):
            if days >= milestone and last_reward < milestone:
                if bonus_msgs > 0:
                    add_messages(user_id, bonus_msgs)
                if bonus_days > 0:
                    add_premium_days(user_id, bonus_days)
                set_streak_reward_level(user_id, milestone)
                reward_text = f"\n\n🏅 Награда за {milestone} дней: {desc}"
                break  # одна награда за раз

        # Прогресс до следующей награды
        next_milestone = None
        for m in sorted(STREAK_MILESTONES.keys()):
            if days < m:
                next_milestone = m
                break

        progress = ""
        if next_milestone:
            progress = f"\n📈 До следующей награды: {next_milestone - days} дн."

        await message.answer(
            f"🎯 Твой streak: {days} {word} подряд!"
            f"{reward_text}{progress}"
        )


@router.callback_query(F.data.startswith("phrase_"))
async def handle_phrase_selection(callback: CallbackQuery):
    """Обработка выбора готовой фразы"""
    await callback.answer()
    phrase_map = {
        "phrase_hello": "Hello!",
        "phrase_how_are_you": "How are you?",
        "phrase_fine_thank_you": "I am fine, thank you",
        "phrase_name": "What is your name?",
        "phrase_goodbye": "Goodbye!",
    }
    selected_phrase = phrase_map.get(callback.data)
    if selected_phrase:
        # Имитируем отправку текстового сообщения
        user_id = callback.from_user.id
        username = callback.from_user.username
        # Показываем "печатает..."
        await callback.message.bot.send_chat_action(user_id, ChatAction.TYPING)
        # Небольшая задержка
        await asyncio.sleep(random.uniform(1.5, 3.0))
        # Обрабатываем как обычное сообщение
        await process_user_message(callback.message, selected_phrase, from_user=callback.from_user)


@router.message(F.voice)
async def handle_voice_message(message: Message):
    """Обработка ГОЛОСОВЫХ сообщений"""
    user_id = message.from_user.id
    username = message.from_user.username

    # Rate limiting
    current_time = time()
    last_time = _last_message_time.get(user_id, 0)
    if current_time - last_time < RATE_LIMIT_SECONDS:
        await message.answer(
            f"⏳ Please wait {RATE_LIMIT_SECONDS} seconds between messages."
        )
        return
    _last_message_time[user_id] = current_time

    # Проверяем/создаём пользователя
    user = get_user(user_id)
    if user and len(user) > 4 and user[4]:
        user_level = user[4]

    if not user:
        create_user(user_id, username or message.from_user.first_name)

    # Проверяем онбординг
    if not is_onboarding_completed(user_id):
        # Кнопка для начала онбординга
        start_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Старт", callback_data="start_onboarding")]
            ]
        )
        await message.answer(
            "👋 Привет! Сначала нужно пройти онбординг, чтобы я мог подобрать уроки под твой уровень.",
            reply_markup=start_kb,
        )
        return

    # ПРОВЕРЯЕМ ЛИМИТЫ С USERNAME
    if not can_send_message(user_id, username):
        await message.answer(
            "You've used all your free messages!\n"
            "Get a subscription to continue practicing English\n"
            "Press button below to see prices!",
            reply_markup=get_main_menu(user_id, username),
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
                reply_markup=get_main_menu(user_id, username),
            )
            return
        # Показываем что услышали
        await message.answer(f'You said: "{user_text}"')
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
            reply_markup=get_main_menu(user_id, username),
        )


@router.message(F.text)
async def handle_text_message(message: Message):
    """Обработка ТЕКСТНЫХ сообщений"""
    user_id = message.from_user.id
    username = message.from_user.username
    user_text = message.text

    # Rate limiting
    current_time = time()
    last_time = _last_message_time.get(user_id, 0)
    if current_time - last_time < RATE_LIMIT_SECONDS:
        await message.answer(
            f"⏳ Please wait {RATE_LIMIT_SECONDS} seconds between messages."
        )
        return
    _last_message_time[user_id] = current_time

    print(f"\n📨 === ПОЛУЧЕНО СООБЩЕНИЕ ===")
    print(f"User ID: {user_id}")
    print(f"Username: {username}")
    print(f"Текст: {user_text}")

    # Игнорируем команды и кнопки
    if user_text.startswith("/") or user_text in [
        "📊 Мой статус",
        "💎 Купить Premium",
        "💎 Продлить Premium",
        "🧠 Очистить память",
        "❓ Помощь",
        "📈 Статистика",
        "🎲 Тема для разговора",
        "🎯 Проверить уровень",
    ]:
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
        # Кнопка для начала онбординга
        start_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Старт", callback_data="start_onboarding")]
            ]
        )
        await message.answer(
            "👋 Привет! Сначала нужно пройти онбординг, чтобы я мог подобрать уроки под твой уровень.",
            reply_markup=start_kb,
        )
        return

    # ПРОВЕРЯЕМ ЛИМИТЫ С USERNAME
    print(f"Проверяю лимиты...")
    can_send = can_send_message(user_id, username)
    print(f"Результат can_send_message: {can_send}")
    if not can_send:
        print(f"Лимит исчерпан!")
        await message.answer(
            "You've used all your free messages!\n"
            "Get a subscription to continue practicing English\n"
            "Press button below to see prices!",
            reply_markup=get_main_menu(user_id, username),
        )
        return

    # Обрабатываем сообщение
    await process_user_message(message, user_text)


@router.callback_query(F.data.startswith("sugg:"))
async def on_suggestion_click(callback: CallbackQuery):
    """Обработка нажатия на inline-подсказку (без кеша)"""
    await callback.answer()
    try:
        # sugg:{text}
        text = callback.data[5:]  # убираем "sugg:"
        if not text:
            raise ValueError("empty text")
    except Exception:
        await callback.answer("Invalid button. Please send a new message.")
        return

    # Удаляем клавиатуру
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    # Обрабатываем как обычное сообщение
    await process_user_message(callback.message, text, from_user=callback.from_user)
