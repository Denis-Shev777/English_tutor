"""
Случайные темы для разговора — помогает пользователям начать практику
"""
import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import get_user, user_get, is_onboarding_completed, reset_conversation
from handlers.keyboards import get_main_menu

router = Router()

TOPICS = [
    {
        "emoji": "☕",
        "name": "At a Cafe",
        "name_ru": "В кафе",
        "desc": "Order drinks, discuss the menu, ask for recommendations",
        "starters": [
            "I'd like to order a coffee",
            "What do you recommend?",
            "Can I get the bill, please?",
        ],
    },
    {
        "emoji": "✈️",
        "name": "Travel & Vacation",
        "name_ru": "Путешествия",
        "desc": "Discuss trips, share experiences, plan adventures",
        "starters": [
            "I'm planning a trip to London",
            "Have you ever been to Japan?",
            "I need to book a hotel",
        ],
    },
    {
        "emoji": "🎬",
        "name": "Movies & TV Shows",
        "name_ru": "Кино и сериалы",
        "desc": "Talk about your favorite films, recommend series",
        "starters": [
            "What's your favorite movie?",
            "I watched a great series recently",
            "Do you prefer comedies or dramas?",
        ],
    },
    {
        "emoji": "🍕",
        "name": "Food & Cooking",
        "name_ru": "Еда и готовка",
        "desc": "Discuss recipes, restaurants, and national cuisine",
        "starters": [
            "Can you cook Italian food?",
            "What's your favorite dish?",
            "I tried sushi for the first time",
        ],
    },
    {
        "emoji": "💼",
        "name": "Job Interview",
        "name_ru": "Собеседование",
        "desc": "Practice answering interview questions in English",
        "starters": [
            "Tell me about yourself",
            "Why should we hire you?",
            "What are your strengths?",
        ],
    },
    {
        "emoji": "🏋️",
        "name": "Health & Fitness",
        "name_ru": "Здоровье и спорт",
        "desc": "Talk about workouts, healthy habits, and wellness",
        "starters": [
            "Do you go to the gym?",
            "I started running every morning",
            "What sport do you like?",
        ],
    },
    {
        "emoji": "📱",
        "name": "Technology",
        "name_ru": "Технологии",
        "desc": "Discuss gadgets, apps, AI, and digital life",
        "starters": [
            "What phone do you use?",
            "Have you tried any AI tools?",
            "Social media is so addictive",
        ],
    },
    {
        "emoji": "🎵",
        "name": "Music",
        "name_ru": "Музыка",
        "desc": "Share favorite artists, genres, and concert experiences",
        "starters": [
            "What kind of music do you like?",
            "Have you been to any concerts?",
            "I can't stop listening to this song",
        ],
    },
    {
        "emoji": "🐾",
        "name": "Pets & Animals",
        "name_ru": "Питомцы",
        "desc": "Talk about your pets, funny animal stories",
        "starters": [
            "Do you have any pets?",
            "I'd love to get a dog",
            "Cats or dogs — what do you prefer?",
        ],
    },
    {
        "emoji": "🏠",
        "name": "Daily Routine",
        "name_ru": "Распорядок дня",
        "desc": "Describe your typical day, morning habits, evenings",
        "starters": [
            "What time do you usually wake up?",
            "Tell me about your morning routine",
            "What do you do after work?",
        ],
    },
    {
        "emoji": "🛍️",
        "name": "Shopping",
        "name_ru": "Шопинг",
        "desc": "Discuss shopping habits, sales, online vs offline",
        "starters": [
            "Do you prefer online shopping?",
            "I'm looking for a new jacket",
            "Black Friday deals are crazy",
        ],
    },
    {
        "emoji": "🎉",
        "name": "Holidays & Celebrations",
        "name_ru": "Праздники",
        "desc": "Talk about traditions, parties, and special occasions",
        "starters": [
            "How do you celebrate New Year?",
            "What's your favorite holiday?",
            "I love birthday parties",
        ],
    },
    {
        "emoji": "📚",
        "name": "Books & Reading",
        "name_ru": "Книги и чтение",
        "desc": "Share book recommendations, discuss genres",
        "starters": [
            "What book are you reading now?",
            "Do you prefer fiction or non-fiction?",
            "I want to read more in English",
        ],
    },
    {
        "emoji": "🌍",
        "name": "Countries & Cultures",
        "name_ru": "Страны и культуры",
        "desc": "Explore traditions, customs, and cultural differences",
        "starters": [
            "What country would you like to visit?",
            "Tell me about your culture",
            "What surprised you about other countries?",
        ],
    },
    {
        "emoji": "🎮",
        "name": "Games & Entertainment",
        "name_ru": "Игры и развлечения",
        "desc": "Video games, board games, hobbies, and fun activities",
        "starters": [
            "Do you play any video games?",
            "What do you do for fun?",
            "I love board games with friends",
        ],
    },
    {
        "emoji": "💭",
        "name": "Dreams & Goals",
        "name_ru": "Мечты и цели",
        "desc": "Talk about ambitions, future plans, and bucket lists",
        "starters": [
            "What's your biggest dream?",
            "Where do you see yourself in 5 years?",
            "I want to learn three languages",
        ],
    },
    {
        "emoji": "🏆",
        "name": "Sports",
        "name_ru": "Спорт",
        "desc": "Discuss teams, competitions, and favorite sports",
        "starters": [
            "Do you follow any sports teams?",
            "Did you watch the last World Cup?",
            "I played basketball in school",
        ],
    },
    {
        "emoji": "🎨",
        "name": "Art & Creativity",
        "name_ru": "Искусство",
        "desc": "Painting, photography, design, and creative hobbies",
        "starters": [
            "Do you have any creative hobbies?",
            "I'd love to learn photography",
            "Have you been to any art museums?",
        ],
    },
    {
        "emoji": "🚗",
        "name": "Cars & Road Trips",
        "name_ru": "Авто и путешествия",
        "desc": "Cars, driving, road trips, and commuting",
        "starters": [
            "Do you have a car?",
            "I love road trips with friends",
            "What's your dream car?",
        ],
    },
    {
        "emoji": "👨‍👩‍👧",
        "name": "Family & Friends",
        "name_ru": "Семья и друзья",
        "desc": "Talk about relationships, childhood memories, traditions",
        "starters": [
            "Tell me about your family",
            "What do you do with your friends?",
            "Do you have any siblings?",
        ],
    },
]


def _build_topic_message(topic: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Формирует текст и клавиатуру для темы."""
    text = (
        f"{topic['emoji']} <b>{topic['name']}</b>\n"
        f"<i>{topic['name_ru']}</i>\n\n"
        f"{topic['desc']}\n\n"
        f"Выбери фразу, чтобы начать разговор:"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"💬 {phrase}", callback_data=f"topic:{phrase[:50]}")]
            for phrase in topic["starters"]
        ]
        + [
            [InlineKeyboardButton(text="🎲 Другая тема", callback_data="topic_random")]
        ]
    )
    return text, keyboard


@router.message(F.text == "🎲 Тема для разговора")
async def random_topic(message: Message):
    """Предложить случайную тему для разговора."""
    user_id = message.from_user.id

    if not is_onboarding_completed(user_id):
        start_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Старт", callback_data="start_onboarding")]
            ]
        )
        await message.answer(
            "👋 Сначала пройди онбординг!",
            reply_markup=start_kb,
        )
        return

    topic = random.choice(TOPICS)
    text, keyboard = _build_topic_message(topic)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "topic_random")
async def topic_random_cb(callback: CallbackQuery):
    """Показать другую случайную тему."""
    await callback.answer()
    topic = random.choice(TOPICS)
    text, keyboard = _build_topic_message(topic)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("topic:"))
async def topic_phrase_click(callback: CallbackQuery):
    """Пользователь выбрал стартовую фразу — запускаем разговор."""
    await callback.answer()
    phrase = callback.data[6:]  # remove "topic:"
    user_id = callback.from_user.id

    # Новая тема должна начинаться с чистого контекста, иначе модель "залипает"
    # на предыдущем обсуждаемом слове/теме.
    reset_conversation(user_id)

    # Убираем кнопки у предыдущего сообщения
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    from handlers.conversation import process_user_message

    await process_user_message(callback.message, phrase, from_user=callback.from_user)
