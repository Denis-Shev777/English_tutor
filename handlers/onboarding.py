from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (
    create_user, get_user, set_user_level,
    mark_onboarding_completed, is_onboarding_completed
)
from logger import get_logger

router = Router()
logger = get_logger('onboarding')

# Описание уровней
LEVEL_DESCRIPTIONS = {
    "A1": "Начинающий - знаю алфавит, простые фразы (Hello, Thank you)",
    "A2": "Элементарный - могу представиться, рассказать о себе",
    "B1": "Средний - могу поддержать беседу на знакомые темы",
    "B2": "Продвинутый - свободно общаюсь, понимаю фильмы"
}

# Проверочные вопросы для каждого уровня (по 3 вопроса)
VERIFICATION_QUESTIONS = {
    "A1": [
        {
            "question": "How do you say 'Привет' in English?",
            "options": ["Hello", "Goodbye", "Please", "Sorry"],
            "correct": 0
        },
        {
            "question": "What is this: 🍎?",
            "options": ["Banana", "Apple", "Orange", "Grape"],
            "correct": 1
        },
        {
            "question": "I ___ a student.",
            "options": ["am", "is", "are", "be"],
            "correct": 0
        }
    ],
    "A2": [
        {
            "question": "I ___ to the cinema yesterday.",
            "options": ["go", "went", "gone", "going"],
            "correct": 1
        },
        {
            "question": "She ___ like coffee.",
            "options": ["don't", "doesn't", "isn't", "aren't"],
            "correct": 1
        },
        {
            "question": "They ___ tennis every weekend.",
            "options": ["play", "plays", "playing", "played"],
            "correct": 0
        }
    ],
    "B1": [
        {
            "question": "If I ___ you, I would take that job.",
            "options": ["am", "was", "were", "be"],
            "correct": 2
        },
        {
            "question": "I've been ___ for this company for 5 years.",
            "options": ["work", "worked", "working", "works"],
            "correct": 2
        },
        {
            "question": "She told me that she ___ the movie before.",
            "options": ["saw", "has seen", "had seen", "would see"],
            "correct": 2
        }
    ],
    "B2": [
        {
            "question": "The project ___ by the end of next month.",
            "options": ["will complete", "will be completed", "completes", "is completing"],
            "correct": 1
        },
        {
            "question": "I wish I ___ more time to study last year.",
            "options": ["have", "had", "had had", "would have"],
            "correct": 2
        },
        {
            "question": "By the time you arrive, we ___ dinner.",
            "options": ["finish", "will finish", "will have finished", "are finishing"],
            "correct": 2
        }
    ]
}

def get_level_selection_keyboard():
    """Клавиатура выбора уровня"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔰 A1 - {LEVEL_DESCRIPTIONS['A1']}", callback_data="level_A1")],
        [InlineKeyboardButton(text=f"📗 A2 - {LEVEL_DESCRIPTIONS['A2']}", callback_data="level_A2")],
        [InlineKeyboardButton(text=f"📘 B1 - {LEVEL_DESCRIPTIONS['B1']}", callback_data="level_B1")],
        [InlineKeyboardButton(text=f"📙 B2 - {LEVEL_DESCRIPTIONS['B2']}", callback_data="level_B2")]
    ])
    return keyboard

@router.callback_query(F.data == "start_onboarding")
async def start_onboarding(callback: CallbackQuery):
    """Начало онбординга"""
    await callback.answer()

    text = (
        "🎯 ДОБРО ПОЖАЛОВАТЬ В ENGLISH TUTOR!\n\n"
        "Давай определим твой уровень английского.\n"
        "Это поможет мне адаптировать обучение под тебя.\n\n"
        "Выбери свой примерный уровень:"
    )

    await callback.message.answer(text, reply_markup=get_level_selection_keyboard())

@router.callback_query(F.data.startswith("level_"))
async def select_level(callback: CallbackQuery):
    """Выбор уровня и начало теста"""
    await callback.answer()

    level = callback.data.split("_")[1]  # A1, A2, B1, B2
    user_id = callback.from_user.id

    questions = VERIFICATION_QUESTIONS[level]
    question_data = questions[0]

    # Формат callback_data: verify_{level}_{question_idx}_{answer_idx}_{current_score}
    # Начинаем с score=0
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=option,
            callback_data=f"verify_{level}_0_{i}_0"
        )] for i, option in enumerate(question_data["options"])
    ])

    text = (
        f"Отлично! Давай проверим уровень {level}.\n\n"
        f"Вопрос 1 из {len(questions)}:\n\n"
        f"{question_data['question']}"
    )

    await callback.message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("verify_"))
async def verify_answer(callback: CallbackQuery):
    """Проверка ответа на вопрос"""
    await callback.answer()

    # Формат: verify_{level}_{question_idx}_{answer_idx}_{current_score}
    parts = callback.data.split("_")
    level = parts[1]
    question_idx = int(parts[2])
    answer_idx = int(parts[3])
    current_score = int(parts[4])

    questions = VERIFICATION_QUESTIONS[level]
    current_question = questions[question_idx]

    # Проверяем ответ
    is_correct = answer_idx == current_question["correct"]
    new_score = current_score + (1 if is_correct else 0)

    # Следующий вопрос
    next_idx = question_idx + 1

    if next_idx < len(questions):
        # Есть еще вопросы
        next_question = questions[next_idx]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=option,
                callback_data=f"verify_{level}_{next_idx}_{i}_{new_score}"
            )] for i, option in enumerate(next_question["options"])
        ])

        feedback = "Правильно! ✅" if is_correct else "Не совсем 🤔"

        text = (
            f"{feedback}\n\n"
            f"Вопрос {next_idx + 1} из {len(questions)}:\n\n"
            f"{next_question['question']}"
        )

        await callback.message.answer(text, reply_markup=keyboard)
    else:
        # Тест завершен - проверяем финальный результат
        total_questions = len(questions)
        final_score = new_score

        # Для прохождения нужно 2 из 3 правильных ответов
        if final_score >= 2:
            # Уровень подтвержден
            await complete_onboarding(callback, level, final_score, total_questions)
        else:
            # Уровень не подтвержден - предлагаем повторить или выбрать другой
            await failed_verification(callback, level, final_score, total_questions)

async def complete_onboarding(callback: CallbackQuery, level: str, score: int, total: int):
    """Завершение онбординга - уровень подтвержден"""
    user_id = callback.from_user.id
    username = callback.from_user.username

    # Создаем пользователя если его нет
    if not get_user(user_id):
        create_user(user_id, username)

    # Сохраняем уровень
    set_user_level(user_id, level)
    mark_onboarding_completed(user_id)

    logger.info(f"Пользователь {user_id} завершил онбординг, уровень: {level}, результат: {score}/{total}")

    text = (
        f"🎉 Отлично! Результат: <b>{score} из {total}</b>\n\n"
        f"✅ Уровень <b>{level}</b> подтвержден!\n"
        f"{LEVEL_DESCRIPTIONS[level]}\n\n"
        f"Теперь я буду адаптировать свои ответы под твой уровень.\n\n"
        f"Начнем практику! Отправь голосовое или текстовое сообщение."
    )

    await callback.message.answer(text)

async def failed_verification(callback: CallbackQuery, level: str, score: int, total: int):
    """Тест не пройден - предложить повторить или выбрать другой уровень"""
    user_id = callback.from_user.id

    logger.info(f"Пользователь {user_id} не прошел тест уровня {level}, результат: {score}/{total}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Пройти тест заново", callback_data=f"level_{level}")],
        [InlineKeyboardButton(text="📝 Выбрать другой уровень", callback_data="choose_different_level")]
    ])

    text = (
        f"Результат: <b>{score} из {total}</b> 🤔\n\n"
        f"Для подтверждения уровня {level} нужно правильно ответить минимум на 2 вопроса из 3.\n\n"
        f"Что ты хочешь сделать?"
    )

    await callback.message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data == "choose_different_level")
async def choose_different_level(callback: CallbackQuery):
    """Выбрать другой уровень после провала теста"""
    await callback.answer()

    text = (
        "Выбери другой уровень английского:\n\n"
        f"<b>A1</b> - {LEVEL_DESCRIPTIONS['A1']}\n"
        f"<b>A2</b> - {LEVEL_DESCRIPTIONS['A2']}\n"
        f"<b>B1</b> - {LEVEL_DESCRIPTIONS['B1']}\n"
        f"<b>B2</b> - {LEVEL_DESCRIPTIONS['B2']}"
    )

    await callback.message.answer(text, reply_markup=get_level_selection_keyboard())

@router.message(Command("change_level"))
@router.message(F.text == "🎓 Изменить уровень")
async def cmd_change_level(message: Message):
    """Изменить уровень английского"""
    user_id = message.from_user.id

    text = (
        "🎓 <b>Изменить уровень английского</b>\n\n"
        "Выбери свой текущий уровень английского:\n\n"
        f"<b>A1</b> - {LEVEL_DESCRIPTIONS['A1']}\n"
        f"<b>A2</b> - {LEVEL_DESCRIPTIONS['A2']}\n"
        f"<b>B1</b> - {LEVEL_DESCRIPTIONS['B1']}\n"
        f"<b>B2</b> - {LEVEL_DESCRIPTIONS['B2']}\n\n"
        "После выбора пройдешь короткий тест для подтверждения."
    )

    await message.answer(text, reply_markup=get_level_selection_keyboard())
