from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command
from handlers.keyboards import get_main_menu
import sys
import os
import random
import string

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (
    create_user,
    get_user,
    set_user_level,
    mark_onboarding_completed,
    is_onboarding_completed,
    set_referral_code,
)
from logger import get_logger

router = Router()
logger = get_logger("onboarding")

# Описание уровней
LEVEL_DESCRIPTIONS = {
    "A1": "Начинающий - знаю алфавит, простые фразы (Hello, Thank you)",
    "A2": "Элементарный - могу представиться, рассказать о себе",
    "B1": "Средний - могу поддержать беседу на знакомые темы",
    "B2": "Продвинутый - свободно общаюсь, понимаю фильмы",
}

# Банк проверочных вопросов для каждого уровня (20-30 вопросов)
# При тестировании будет выбрано случайных 3 вопроса
VERIFICATION_QUESTIONS_BANK = {
    "A1": [
        {"question": "How do you say 'Привет' in English?", "options": ["Hello", "Goodbye", "Please", "Sorry"], "correct": 0},
        {"question": "What is this: 🍎?", "options": ["Banana", "Apple", "Orange", "Grape"], "correct": 1},
        {"question": "Choose the correct word: I ___ Denis.", "options": ["am", "is", "are", "be"], "correct": 0},
        {"question": "My name ___ Maria.", "options": ["am", "is", "are", "be"], "correct": 1},
        {"question": "What is this: 🐶?", "options": ["Cat", "Dog", "Bird", "Fish"], "correct": 1},
        {"question": "How do you say 'Спасибо' in English?", "options": ["Hello", "Sorry", "Thank you", "Goodbye"], "correct": 2},
        {"question": "I ___ a student.", "options": ["am", "is", "are", "be"], "correct": 0},
        {"question": "She ___ a teacher.", "options": ["am", "is", "are", "be"], "correct": 1},
        {"question": "What is this: 🏠?", "options": ["School", "House", "Car", "Book"], "correct": 1},
        {"question": "They ___ friends.", "options": ["am", "is", "are", "be"], "correct": 2},
        {"question": "This is ___ book.", "options": ["a", "an", "the", "-"], "correct": 0},
        {"question": "I have ___ apple.", "options": ["a", "an", "the", "-"], "correct": 1},
        {"question": "How do you say 'Пока' in English?", "options": ["Hello", "Goodbye", "Thanks", "Sorry"], "correct": 1},
        {"question": "What color is the sky?", "options": ["Red", "Blue", "Green", "Yellow"], "correct": 1},
        {"question": "I ___ happy.", "options": ["am", "is", "are", "be"], "correct": 0},
        {"question": "We ___ students.", "options": ["am", "is", "are", "be"], "correct": 2},
        {"question": "What is this: 📚?", "options": ["Book", "Pen", "Table", "Chair"], "correct": 0},
        {"question": "He ___ a doctor.", "options": ["am", "is", "are", "be"], "correct": 1},
        {"question": "I like ___.", "options": ["read", "reading", "reads", "to reading"], "correct": 1},
        {"question": "This is ___ orange.", "options": ["a", "an", "the", "-"], "correct": 1},
    ],
    "A2": [
        {"question": "I ___ to the cinema yesterday.", "options": ["go", "went", "gone", "going"], "correct": 1},
        {"question": "She ___ like coffee.", "options": ["don't", "doesn't", "isn't", "aren't"], "correct": 1},
        {"question": "Where ___ you live?", "options": ["do", "does", "did", "are"], "correct": 0},
        {"question": "I ___ TV every evening.", "options": ["watch", "watches", "watching", "watched"], "correct": 0},
        {"question": "He ___ to work by bus.", "options": ["go", "goes", "going", "gone"], "correct": 1},
        {"question": "We ___ pizza last night.", "options": ["eat", "eats", "ate", "eating"], "correct": 2},
        {"question": "They ___ playing football now.", "options": ["is", "are", "am", "be"], "correct": 1},
        {"question": "I ___ see him tomorrow.", "options": ["will", "would", "can", "must"], "correct": 0},
        {"question": "She ___ born in 1995.", "options": ["is", "was", "were", "has"], "correct": 1},
        {"question": "How ___ books do you have?", "options": ["much", "many", "lot", "few"], "correct": 1},
        {"question": "There ___ a cat in the garden.", "options": ["is", "are", "am", "be"], "correct": 0},
        {"question": "I ___ English for 2 years.", "options": ["study", "studies", "am studying", "have studied"], "correct": 3},
        {"question": "He can ___ very fast.", "options": ["run", "runs", "running", "ran"], "correct": 0},
        {"question": "We ___ to the beach last summer.", "options": ["go", "goes", "went", "gone"], "correct": 2},
        {"question": "She ___ cooking dinner now.", "options": ["is", "are", "am", "be"], "correct": 0},
        {"question": "I ___ coffee every morning.", "options": ["drink", "drinks", "drinking", "drank"], "correct": 0},
        {"question": "They ___ to London last year.", "options": ["go", "goes", "went", "gone"], "correct": 2},
        {"question": "How ___ water do you need?", "options": ["much", "many", "lot", "few"], "correct": 0},
        {"question": "I ___ my homework yesterday.", "options": ["do", "does", "did", "done"], "correct": 2},
        {"question": "She ___ to school every day.", "options": ["walk", "walks", "walking", "walked"], "correct": 1},
    ],
    "B1": [
        {"question": "If I ___ you, I would take that job.", "options": ["am", "was", "were", "be"], "correct": 2},
        {"question": "I've been ___ for this company for 5 years.", "options": ["work", "worked", "working", "works"], "correct": 2},
        {"question": "I would rather ___ at home tonight.", "options": ["stay", "staying", "to stay", "stayed"], "correct": 0},
        {"question": "She said she ___ come to the party.", "options": ["will", "would", "can", "must"], "correct": 1},
        {"question": "I've never ___ sushi before.", "options": ["eat", "ate", "eaten", "eating"], "correct": 2},
        {"question": "By the time I arrived, they ___ already left.", "options": ["have", "has", "had", "having"], "correct": 2},
        {"question": "I wish I ___ more time yesterday.", "options": ["have", "had", "has", "having"], "correct": 1},
        {"question": "The book ___ by millions of people.", "options": ["read", "reads", "is read", "was read"], "correct": 2},
        {"question": "I'm not used ___ so early.", "options": ["wake up", "to wake up", "to waking up", "waking up"], "correct": 2},
        {"question": "If you ___ harder, you would pass the exam.", "options": ["study", "studied", "had studied", "have studied"], "correct": 1},
        {"question": "She's been living here ___ 2010.", "options": ["since", "for", "from", "at"], "correct": 0},
        {"question": "I'd rather you ___ smoke in here.", "options": ["don't", "didn't", "doesn't", "not"], "correct": 1},
        {"question": "He suggested ___ to the cinema.", "options": ["go", "to go", "going", "went"], "correct": 2},
        {"question": "I'm looking forward ___ you again.", "options": ["see", "to see", "to seeing", "seeing"], "correct": 2},
        {"question": "The movie was ___ than I expected.", "options": ["good", "better", "best", "well"], "correct": 1},
        {"question": "I ___ to Paris three times.", "options": ["go", "went", "have been", "had been"], "correct": 2},
        {"question": "If I had known, I ___ you.", "options": ["tell", "told", "would tell", "would have told"], "correct": 3},
        {"question": "She made me ___ for her.", "options": ["wait", "to wait", "waiting", "waited"], "correct": 0},
        {"question": "I'm tired of ___ the same thing every day.", "options": ["do", "to do", "doing", "done"], "correct": 2},
        {"question": "The house ___ painted last month.", "options": ["is", "was", "has", "had"], "correct": 1},
    ],
    "B2": [
        {"question": "The project ___ by the end of next month.", "options": ["will complete", "will be completed", "completes", "is completing"], "correct": 1},
        {"question": "I wish I ___ more time to study last year.", "options": ["have", "had", "had had", "would have"], "correct": 2},
        {"question": "Hardly ___ finished when the phone rang.", "options": ["I had", "had I", "I have", "have I"], "correct": 1},
        {"question": "The report needs ___ by tomorrow.", "options": ["finish", "to finish", "finishing", "to be finished"], "correct": 3},
        {"question": "Not only ___ late, but he also forgot the documents.", "options": ["he was", "was he", "he is", "is he"], "correct": 1},
        {"question": "Were it not for your help, I ___ failed.", "options": ["will have", "would have", "had", "have"], "correct": 1},
        {"question": "She's accustomed ___ hard.", "options": ["work", "to work", "to working", "working"], "correct": 2},
        {"question": "Scarcely ___ arrived when the meeting started.", "options": ["I had", "had I", "I have", "have I"], "correct": 1},
        {"question": "The manuscript ___ to the publisher next week.", "options": ["will send", "will be sent", "is sending", "sends"], "correct": 1},
        {"question": "He acts as if he ___ the owner.", "options": ["is", "was", "were", "be"], "correct": 2},
        {"question": "I'd sooner you ___ tell anyone about this.", "options": ["don't", "didn't", "doesn't", "not"], "correct": 1},
        {"question": "No sooner ___ than it started to rain.", "options": ["we left", "we had left", "had we left", "did we leave"], "correct": 2},
        {"question": "The book is worthy of ___.", "options": ["read", "to read", "reading", "being read"], "correct": 3},
        {"question": "Little ___ know what was waiting for him.", "options": ["he did", "did he", "he", "does he"], "correct": 1},
        {"question": "I object to ___ like a child.", "options": ["treat", "treating", "being treated", "be treated"], "correct": 2},
        {"question": "Should you ___ any problems, call me immediately.", "options": ["have", "had", "having", "to have"], "correct": 0},
        {"question": "The treaty ___ by both parties yesterday.", "options": ["signed", "was signed", "has signed", "is signed"], "correct": 1},
        {"question": "I have my car ___ every year.", "options": ["service", "serviced", "servicing", "to service"], "correct": 1},
        {"question": "On no account ___ leave the building.", "options": ["you must", "must you", "you should", "should you"], "correct": 1},
        {"question": "He speaks English as though he ___ a native speaker.", "options": ["is", "was", "were", "be"], "correct": 2},
    ],
}


# Хранилище выбранных вопросов для каждого пользователя
# user_id: [question1, question2, question3]
user_test_questions = {}


def get_random_questions(level: str, count: int = 3):
    """Выбрать случайные N вопросов из банка для уровня"""
    questions_bank = VERIFICATION_QUESTIONS_BANK.get(level, [])
    if len(questions_bank) < count:
        return questions_bank
    return random.sample(questions_bank, count)


def get_level_selection_keyboard():
    """Клавиатура выбора уровня"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🔰 A1 - {LEVEL_DESCRIPTIONS['A1']}", callback_data="level_A1"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"📗 A2 - {LEVEL_DESCRIPTIONS['A2']}", callback_data="level_A2"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"📘 B1 - {LEVEL_DESCRIPTIONS['B1']}", callback_data="level_B1"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"📙 B2 - {LEVEL_DESCRIPTIONS['B2']}", callback_data="level_B2"
                )
            ],
        ]
    )
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

    # Выбираем случайные 3 вопроса из банка
    questions = get_random_questions(level, count=3)

    # Сохраняем выбранные вопросы для этого пользователя
    user_test_questions[user_id] = questions

    question_data = questions[0]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=option, callback_data=f"verify_{level}_0_{i}_0")]
            for i, option in enumerate(question_data["options"])
        ]
    )

    text = (
        f"Отлично! Давай проверим уровень {level}.\n\n"
        f"Вопрос 1 из {len(questions)}:\n\n"
        f"{question_data['question']}"
    )

    await callback.message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("verify_"))
async def verify_answer(callback: CallbackQuery):
    """Проверка ответа на вопрос + правило 2/3"""
    await callback.answer()

    parts = callback.data.split("_")
    # verify_{level}_{question_idx}_{answer_idx}_{score}
    level = parts[1]
    question_idx = int(parts[2])
    answer_idx = int(parts[3])
    score = int(parts[4])

    user_id = callback.from_user.id

    # Берем вопросы из сохраненных для этого пользователя
    questions = user_test_questions.get(user_id, get_random_questions(level, count=3))
    current_question = questions[question_idx]

    is_correct = answer_idx == current_question["correct"]
    if is_correct:
        score += 1

    next_idx = question_idx + 1

    # Ещё есть вопросы — показываем следующий
    if next_idx < len(questions):
        next_question = questions[next_idx]

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=option,
                        callback_data=f"verify_{level}_{next_idx}_{i}_{score}",
                    )
                ]
                for i, option in enumerate(next_question["options"])
            ]
        )

        feedback = "Правильно! ✅" if is_correct else "Не совсем 🤔"
        text = (
            f"{feedback}\n\n"
            f"Вопрос {next_idx + 1} из {len(questions)}:\n\n"
            f"{next_question['question']}"
        )
        await callback.message.answer(text, reply_markup=keyboard)
        return

    # Вопросы закончились — решаем по правилу 2 из 3
    passed = score >= 2

    if passed:
        # Очищаем сохраненные вопросы
        user_test_questions.pop(user_id, None)
        await complete_onboarding(callback, level, last_correct=True)
        return

    # ❌ Провал: НЕ завершаем онбординг. Даем выбор: пройти заново или выбрать уровень.
    retry_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔁 Пройти вопросы заново", callback_data=f"retry_{level}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Выбрать другой уровень", callback_data="start_onboarding"
                )
            ],
        ]
    )

    await callback.message.answer(
        f"Похоже, уровень <b>{level}</b> пока сложноват 😅\n"
        f"Результат: <b>{score} / {len(questions)}</b>\n\n"
        f"Хочешь пройти вопросы заново или выбрать другой уровень?",
        reply_markup=retry_kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("retry_"))
async def retry_questions(callback: CallbackQuery):
    await callback.answer()
    level = callback.data.split("_")[1]
    user_id = callback.from_user.id

    # Выбираем НОВЫЕ случайные 3 вопроса из банка
    questions = get_random_questions(level, count=3)

    # Сохраняем выбранные вопросы для этого пользователя
    user_test_questions[user_id] = questions

    question_data = questions[0]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=option, callback_data=f"verify_{level}_0_{i}_0")]
            for i, option in enumerate(question_data["options"])
        ]
    )

    text = (
        f"Ок! Повторим проверку уровня {level}.\n\n"
        f"Вопрос 1 из {len(questions)}:\n\n"
        f"{question_data['question']}"
    )
    await callback.message.answer(text, reply_markup=keyboard)


def generate_referral_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


async def complete_onboarding(callback: CallbackQuery, level: str, last_correct: bool):
    """Завершение онбординга + генерация реферального кода"""
    user_id = callback.from_user.id
    username = callback.from_user.username

    # Создаём пользователя если его нет
    if not get_user(user_id):
        create_user(user_id, username)

    # Сохраняем уровень и завершаем онбординг
    set_user_level(user_id, level)
    mark_onboarding_completed(user_id)

    # Генерируем реферальный код только если его ещё нет
    user = get_user(user_id)
    existing_code = user[8] if user and len(user) > 8 else None
    if not existing_code:
        referral_code = generate_referral_code()
        set_referral_code(user_id, referral_code)
    else:
        referral_code = existing_code

    logger.info(
        f"Пользователь {user_id} завершил онбординг, уровень: {level}, реферальный код: {referral_code}"
    )

    feedback = "Отлично! ✅" if last_correct else "Хорошая попытка! 👍"

    # Бейджи персонажей
    BADGES = {
        "A1": "🐣 Цыплёнок (Beginner Chick)",
        "A2": "🦊 Лисёнок (Curious Fox)",
        "B1": "🦁 Лев (Confident Lion)",
        "B2": "🦅 Орёл (Soaring Eagle)",
    }
    badge = BADGES.get(level, "🐣 Цыплёнок")

    text = (
        f"{feedback}\n\n"
        f"🎉 Онбординг завершен!\n\n"
        f"Твой уровень: <b>{level}</b>\n"
        f"Твой персонаж: {badge}\n\n"
        f"{LEVEL_DESCRIPTIONS[level]}\n\n"
        f"Теперь я буду адаптировать ответы под твой уровень.\n"
        f"Начнем практику! Отправь голосовое или текстовое сообщение.\n\n"
        f"💡 Нажми <b>🎲 Тема для разговора</b> если не знаешь о чём поговорить!"
    )

    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_main_menu(user_id, username),
    )

    await callback.message.answer(
        "✅ Меню включено",
        reply_markup=get_main_menu(user_id, username),
    )
