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

# Проверочные вопросы для каждого уровня
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
    
    # Сохраняем временно выбранный уровень (подтвердим после теста)
    # Сохраняем в callback_data первого вопроса
    
    questions = VERIFICATION_QUESTIONS[level]
    question_data = questions[0]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=option, 
            callback_data=f"verify_{level}_0_{i}"
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
    
    # Формат: verify_A1_0_1 (level_questionIndex_answerIndex)
    parts = callback.data.split("_")
    level = parts[1]
    question_idx = int(parts[2])
    answer_idx = int(parts[3])
    
    questions = VERIFICATION_QUESTIONS[level]
    current_question = questions[question_idx]
    
    # Проверяем ответ
    is_correct = answer_idx == current_question["correct"]
    
    # Следующий вопрос
    next_idx = question_idx + 1
    
    if next_idx < len(questions):
        # Есть еще вопросы
        next_question = questions[next_idx]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=option,
                callback_data=f"verify_{level}_{next_idx}_{i}"
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
        # Тест завершен
        await complete_onboarding(callback, level, is_correct)

async def complete_onboarding(callback: CallbackQuery, level: str, last_correct: bool):
    """Завершение онбординга"""
    user_id = callback.from_user.id
    username = callback.from_user.username
    
    # Создаем пользователя если его нет
    if not get_user(user_id):
        create_user(user_id, username)
    
    # Сохраняем уровень
    set_user_level(user_id, level)
    mark_onboarding_completed(user_id)
    
    logger.info(f"Пользователь {user_id} завершил онбординг, уровень: {level}")
    
    feedback = "Отлично! ✅" if last_correct else "Хорошая попытка! 👍"
    
    text = (
        f"{feedback}\n\n"
        f"🎉 Онбординг завершен!\n\n"
        f"Твой уровень: **{level}**\n"
        f"{LEVEL_DESCRIPTIONS[level]}\n\n"
        f"Теперь я буду адаптировать свои ответы под твой уровень.\n\n"
        f"Начнем практику! Отправь голосовое или текстовое сообщение."
    )
    
    await callback.message.answer(text, parse_mode="Markdown")
