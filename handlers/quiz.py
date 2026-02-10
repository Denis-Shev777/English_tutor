"""
30-секундный вирусный квиз — «Проверь свой English за 30 секунд!»
Запускается через deep link:  t.me/bot?start=quiz30
"""
import random
from urllib.parse import quote
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import get_user, create_user

router = Router()

# --- Хранилище состояния квиза (in-memory) ---
quiz_state: dict[int, dict] = {}

# --- Банк вопросов (отличается от онбординга) ---
QUIZ_QUESTIONS = [
    # A1 — Elementary
    {
        "q": 'She ___ a teacher.',
        "options": ["is", "are", "am", "be"],
        "correct": 0,
        "level": "A1",
    },
    {
        "q": '"___ you speak English?"',
        "options": ["Do", "Does", "Is", "Are"],
        "correct": 0,
        "level": "A1",
    },
    {
        "q": 'I ___ breakfast every morning.',
        "options": ["have", "has", "having", "had"],
        "correct": 0,
        "level": "A1",
    },
    {
        "q": 'This is ___ interesting book.',
        "options": ["an", "a", "the", "—"],
        "correct": 0,
        "level": "A1",
    },
    # A2 — Pre-Intermediate
    {
        "q": 'He ___ to Paris last summer.',
        "options": ["went", "go", "has gone", "going"],
        "correct": 0,
        "level": "A2",
    },
    {
        "q": 'She is ___ than her brother.',
        "options": ["taller", "more tall", "tallest", "tall"],
        "correct": 0,
        "level": "A2",
    },
    {
        "q": 'There aren\'t ___ eggs in the fridge.',
        "options": ["any", "some", "a", "the"],
        "correct": 0,
        "level": "A2",
    },
    {
        "q": 'I ___ TV when the phone rang.',
        "options": ["was watching", "watched", "watch", "am watching"],
        "correct": 0,
        "level": "A2",
    },
    # B1 — Intermediate
    {
        "q": 'If I ___ rich, I would travel the world.',
        "options": ["were", "am", "be", "will be"],
        "correct": 0,
        "level": "B1",
    },
    {
        "q": 'I ___ here since 2020.',
        "options": ["have lived", "am living", "live", "lived"],
        "correct": 0,
        "level": "B1",
    },
    {
        "q": 'The letter ___ yesterday.',
        "options": ["was sent", "sent", "is sending", "sends"],
        "correct": 0,
        "level": "B1",
    },
    {
        "q": 'She asked me where I ___.',
        "options": ["lived", "live", "am living", "do live"],
        "correct": 0,
        "level": "B1",
    },
    # B2 — Upper-Intermediate
    {
        "q": 'Had I known earlier, I ___ differently.',
        "options": ["would have acted", "acted", "will act", "would act"],
        "correct": 0,
        "level": "B2",
    },
    {
        "q": '___ the heavy rain, we decided to go out.',
        "options": ["Despite", "Although", "However", "Because"],
        "correct": 0,
        "level": "B2",
    },
    {
        "q": 'She suggested ___ a short break.',
        "options": ["taking", "to take", "take", "taken"],
        "correct": 0,
        "level": "B2",
    },
    {
        "q": 'Not only ___ late, but he also forgot the keys.',
        "options": ["was he", "he was", "is he", "he is"],
        "correct": 0,
        "level": "B2",
    },
]

# Badges для уровней
LEVEL_BADGES = {
    "A1": {"emoji": "🐣", "name": "Beginner Chick"},
    "A2": {"emoji": "🦊", "name": "Curious Fox"},
    "B1": {"emoji": "🦁", "name": "Confident Lion"},
    "B2": {"emoji": "🦅", "name": "Soaring Eagle"},
}


def _select_quiz_questions(count: int = 5) -> list[dict]:
    """Выбирает сбалансированный набор вопросов для квиза."""
    by_level = {}
    for q in QUIZ_QUESTIONS:
        by_level.setdefault(q["level"], []).append(q)

    selected = []
    # По 1 вопросу каждого уровня + 1 случайный
    for level in ["A1", "A2", "B1", "B2"]:
        if by_level.get(level):
            selected.append(random.choice(by_level[level]))

    remaining = [q for q in QUIZ_QUESTIONS if q not in selected]
    if remaining:
        selected.append(random.choice(remaining))

    random.shuffle(selected)
    return selected[:count]


def _estimate_level(score: int) -> str:
    """Оценивает уровень по количеству правильных ответов."""
    if score <= 1:
        return "A1"
    elif score == 2:
        return "A2"
    elif score == 3:
        return "B1"
    else:
        return "B2"


def _build_question_message(state: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Формирует текст и кнопки для текущего вопроса."""
    idx = state["current"]
    total = len(state["questions"])
    q = state["questions"][idx]

    # Прогресс-бар
    filled = "🟢" * idx + "⚪" * (total - idx)

    text = (
        f"<b>Вопрос {idx + 1}/{total}</b>  {filled}\n\n"
        f"<code>{q['q']}</code>"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=option,
                    callback_data=f"qz:{idx}:{i}",
                )
            ]
            for i, option in enumerate(q["options"])
        ]
    )
    return text, keyboard


async def start_quiz(message: Message):
    """Запускает 30-секундный квиз."""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    # Создаём пользователя если нет
    user = get_user(user_id)
    if not user:
        create_user(user_id, username)

    questions = _select_quiz_questions(5)
    quiz_state[user_id] = {
        "questions": questions,
        "current": 0,
        "score": 0,
    }

    # Приветственное сообщение
    await message.answer(
        "🎓 <b>Экспресс-тест по английскому!</b>\n\n"
        "5 вопросов — проверь свой уровень.\n"
        "Выбирай правильный ответ:",
        parse_mode="HTML",
    )

    text, keyboard = _build_question_message(quiz_state[user_id])
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("qz:"))
async def quiz_answer(callback: CallbackQuery):
    """Обработка ответа на вопрос квиза."""
    await callback.answer()
    user_id = callback.from_user.id

    state = quiz_state.get(user_id)
    if not state:
        await callback.message.edit_text("Квиз завершён или не был начат. Попробуй /start quiz30")
        return

    # Парсим callback: qz:{question_idx}:{answer_idx}
    parts = callback.data.split(":")
    q_idx = int(parts[1])
    a_idx = int(parts[2])

    # Защита от повторного нажатия
    if q_idx != state["current"]:
        return

    question = state["questions"][q_idx]
    is_correct = a_idx == question["correct"]

    if is_correct:
        state["score"] += 1

    # Показываем результат ответа
    correct_text = question["options"][question["correct"]]
    if is_correct:
        feedback = f"✅ Правильно! <b>{correct_text}</b>"
    else:
        chosen = question["options"][a_idx]
        feedback = f"❌ <b>{chosen}</b> → Правильно: <b>{correct_text}</b>"

    state["current"] += 1

    # Есть ещё вопросы?
    if state["current"] < len(state["questions"]):
        next_text, next_kb = _build_question_message(state)
        await callback.message.edit_text(
            f"{feedback}\n\n{next_text}",
            reply_markup=next_kb,
            parse_mode="HTML",
        )
    else:
        # Квиз завершён — показываем результат
        score = state["score"]
        total = len(state["questions"])
        level = _estimate_level(score)
        badge = LEVEL_BADGES[level]

        stars = "⭐" * score + "☆" * (total - score)

        # Получаем username бота для шеринга
        bot_info = await callback.bot.get_me()
        bot_username = bot_info.username
        share_text = quote(f"Я набрал {score}/{total} в тесте по английскому! Проверь свой уровень:")
        share_url = quote(f"https://t.me/{bot_username}?start=quiz30")

        result_text = (
            f"{feedback}\n\n"
            f"{'─' * 20}\n\n"
            f"🎓 <b>Результат квиза</b>\n\n"
            f"{stars}\n"
            f"Правильных ответов: <b>{score}/{total}</b>\n\n"
            f"Примерный уровень: {badge['emoji']} <b>{level} — {badge['name']}</b>\n\n"
        )

        if score <= 2:
            result_text += "Не расстраивайся — практика делает чудеса! 💪"
        elif score <= 4:
            result_text += "Отличный результат! Продолжай в том же духе! 🔥"
        else:
            result_text += "Великолепно! Ты настоящий профи! 🏆"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📤 Поделиться результатом",
                        url=f"https://t.me/share/url?text={share_text}&url={share_url}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Пройти ещё раз",
                        callback_data="quiz_restart",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🚀 Начать практику",
                        callback_data="start_onboarding",
                    )
                ],
            ]
        )

        await callback.message.edit_text(
            result_text, reply_markup=keyboard, parse_mode="HTML"
        )

        # Очищаем состояние
        quiz_state.pop(user_id, None)


@router.callback_query(F.data == "quiz_restart")
async def quiz_restart(callback: CallbackQuery):
    """Перезапуск квиза."""
    await callback.answer()
    await start_quiz(callback.message)
