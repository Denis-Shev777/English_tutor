from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import sys
import os
from datetime import datetime
from dotenv import load_dotenv
from database import user_get


# Загружаем .env
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (
    get_user,
    create_user,
    reset_conversation,
    get_subscription,
    has_active_subscription,
    get_total_users,
    get_active_subscriptions,
    is_onboarding_completed,
    get_users_by_level,
    get_average_messages,
    get_user_id_by_referral_code,
    add_referral,
    add_messages,
    add_premium_days,
)

from handlers.keyboards import get_main_menu, get_buy_menu

# Получаем WHITELIST из .env
WHITELIST_USERNAMES = os.getenv("WHITELIST_USERNAMES", "").split(",")

# Персонажи-бейджи для каждого уровня
LEVEL_BADGES = {
    "A1": {"emoji": "🐣", "name": "Цыплёнок", "title": "Beginner Chick", "desc": "Делает первые шаги в английском"},
    "A2": {"emoji": "🦊", "name": "Лисёнок", "title": "Curious Fox", "desc": "Уверенно осваивает основы"},
    "B1": {"emoji": "🦁", "name": "Лев", "title": "Confident Lion", "desc": "Свободно говорит на повседневные темы"},
    "B2": {"emoji": "🦅", "name": "Орёл", "title": "Soaring Eagle", "desc": "Покоряет вершины английского"},
}

# Streak-награды
STREAK_MILESTONES = {3: 5, 7: 10, 14: 20, 30: 0}  # дней: бонус сообщений (30=premium)

router = Router()


def is_vip(username: str) -> bool:
    """
    Проверяет, является ли пользователь VIP
    по WHITELIST_USERNAMES из .env
    """
    if not username:
        return False

    raw = os.getenv("WHITELIST_USERNAMES", "")
    vip_usernames = {u.strip() for u in raw.split(",") if u.strip()}

    return username in vip_usernames


@router.message(Command("start", ignore_case=True))
async def cmd_start(message: Message):
    """Команда /start"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    # Создаём пользователя если не существует
    user = get_user(user_id)
    args = message.text.split(maxsplit=1)
    payload = args[1] if len(args) > 1 else None

    # --- Referral activation with bonuses ---
    parts = (message.text or "").split(maxsplit=1)
    payload = parts[1].strip() if len(parts) > 1 else None

    # --- Viral quiz deep link ---
    if payload == "quiz30":
        from handlers.quiz import start_quiz
        await start_quiz(message)
        return

    if payload and payload.startswith("REF_"):
        referral_code = payload[4:].strip()

        inviter_id = get_user_id_by_referral_code(referral_code)
        if not inviter_id:
            await message.answer("❌ Реферальный код не найден.")
            return

        if inviter_id == user_id:
            await message.answer(
                "❌ Нельзя активировать свою собственную реферальную ссылку."
            )
            return

        # inviter status
        inviter_is_vip = is_vip(get_user(inviter_id)[1])
        inviter_is_premium = has_active_subscription(inviter_id)

        if not inviter_is_vip and not inviter_is_premium:
            await message.answer(
                "❌ Этот пользователь не может отправлять реферальные ссылки."
            )
            return

        ok = add_referral(
            inviter_id=inviter_id, invitee_id=user_id, referral_code=referral_code
        )
        if not ok:
            await message.answer("ℹ️ Реферальный бонус уже был активирован ранее.")
            return

        # invitee status
        invitee_is_vip = is_vip(username)
        invitee_is_premium = has_active_subscription(user_id)

        # Бонус приглашаемому
        if invitee_is_vip:
            await message.answer(
                "✅ Реферальный код принят! Ты уже VIP — бонус не требуется."
            )
        elif invitee_is_premium:
            add_premium_days(user_id, 1)
            await message.answer(
                "🎁 Бонус активирован! Твоя Premium-подписка продлена на 1 день."
            )
        else:
            add_messages(user_id, 50)
            await message.answer("🎁 Бонус активирован! Тебе начислено +50 сообщений.")

        # Бонус пригласившему
        if inviter_is_premium and not inviter_is_vip:
            add_premium_days(inviter_id, 1)

    # --- /Referral activation ---

    if not user:
        create_user(user_id, username)

    # Проверяем онбординг
    if not is_onboarding_completed(user_id):
        # Запускаем онбординг для новых пользователей
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🚀 Начать!", callback_data="start_onboarding"
                    )
                ]
            ]
        )

        await message.answer(
            f"Привет, {username}! 👋\n\n"
            "Я твой помощник для практики английского! 🎓\n\n"
            "<b>Что я умею:</b>\n"
            "• Практика разговорной речи (голос и текст)\n"
            "• Мягкие исправления ошибок\n"
            "• Помощь с грамматикой и словами\n"
            "• Адаптация под твой уровень\n\n"
            "Давай начнем с определения твоего уровня!",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        return

    # Обычное приветствие для пользователей с онбордингом
    await message.answer(
        f"Привет, {username}!\n\n"
        "Я твой помощник для практики английского! 🎓\n\n"
        "<b>Как использовать:</b>\n"
        "• Отправляй голосовые или текстовые сообщения на английском\n"
        "• Я помогу тебе практиковать разговорную речь\n"
        "• Мягко исправлю твои ошибки\n"
        "• Спрашивай о словах, грамматике или просто общайся!\n\n"
        "<b>Бесплатно:</b> 25 сообщений\n"
        "<b>Premium:</b> Безлимитный доступ всего за <b>100 Stars</b>/неделю\n\n"
        "Используй кнопки ниже для быстрого доступа! ⬇️",
        reply_markup=get_main_menu(user_id, username),
        parse_mode="HTML",
    )


@router.message(F.text == "📊 Мой статус")
@router.message(Command("status"))
async def cmd_status(message: Message):
    """Команда /status или кнопка"""
    user_id = message.from_user.id
    username = message.from_user.username
    user = get_user(user_id)

    if not user:
        start_kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🚀 Старт", callback_data="go_start")]]
        )
        await message.answer(
            "❌ Пользователь не найден. Нажмите кнопку ниже:",
            reply_markup=start_kb,
        )
        return

    # Получаем streak и уровень
    streak = user[7] if len(user) > 7 else 0
    level = user_get(user, "level", "A1") or "A1"
    badge = LEVEL_BADGES.get(level, LEVEL_BADGES["A1"])
    badge_line = f"{badge['emoji']} <b>{level} — {badge['name']}</b> ({badge['title']})"

    # Streak прогресс
    next_milestone = None
    for m in sorted(STREAK_MILESTONES.keys()):
        if streak < m:
            next_milestone = m
            break
    streak_progress = f" (до награды: {next_milestone - streak} дн.)" if next_milestone else " 🏆 Все награды получены!"

    # Белый список по username
    if username and username in WHITELIST_USERNAMES:
        referral_code = user[8] if len(user) > 8 else "Не сгенерирован"
        await message.answer(
            f"⭐ <b>VIP Статус</b>\n\n"
            f"Персонаж: {badge_line}\n"
            f"Streak: {streak} дн. подряд 🎯{streak_progress}\n\n"
            f"У вас неограниченный доступ!\n"
            f"Подписка: Пожизненный Premium 💎\n"
            f"Реферальный код: <code>{referral_code}</code>",
            reply_markup=get_main_menu(user_id, username),
            parse_mode="HTML",
        )
        return

    # Проверяем подписку
    subscription = get_subscription(user_id)

    if has_active_subscription(user_id) and subscription:
        expires = datetime.fromisoformat(subscription[1])
        time_left = expires - datetime.now()
        if time_left.days > 0:
            time_info = f"Дней осталось: {time_left.days}"
        else:
            hours_left = time_left.seconds // 3600
            time_info = f"Часов осталось: {hours_left}"

        referral_code = user[8] if len(user) > 8 else "Не сгенерирован"
        await message.answer(
            f"✅ <b>Premium активен</b>\n\n"
            f"Персонаж: {badge_line}\n"
            f"Streak: {streak} дн. подряд 🎯{streak_progress}\n\n"
            f"Статус: Premium 💎\n"
            f"Истекает: {expires.strftime('%Y-%m-%d %H:%M')}\n"
            f"{time_info}\n"
            f"Реферальный код: <code>{referral_code}</code>\n\n"
            f"Продолжайте в том же духе!",
            reply_markup=get_main_menu(user_id, username),
            parse_mode="HTML",
        )
    else:
        BASE_LIMIT = 25

        messages_used = int(user_get(user, "message_count", 0))  # message_count
        bonus_messages = int(
            user_get(user, "messages_count", 0)
        )  # messages_count (бонус)
        total_limit = BASE_LIMIT + bonus_messages
        messages_left = max(0, total_limit - messages_used)

        if messages_left > 0:
            bonus_line = (
                f"🎁 Бонус сообщений: +{bonus_messages}\n" if bonus_messages > 0 else ""
            )
            await message.answer(
                f"📊 <b>Бесплатный уровень</b>\n\n"
                f"Персонаж: {badge_line}\n"
                f"Streak: {streak} дн. подряд 🎯{streak_progress}\n\n"
                f"{bonus_line}"
                f"Использовано сообщений: {messages_used}/{total_limit}\n"
                f"Осталось: {messages_left}\n\n"
                f"Хотите неограниченный доступ?\n"
                f"Получите Premium всего за <b>100 Stars</b>/неделя!\n\n"
                f"Нажмите кнопку ниже, чтобы обновить! ⬇️",
                reply_markup=get_main_menu(user_id, username),
                parse_mode="HTML",
            )
        else:
            await message.answer(
                f"🚫 <b>Сообщения закончились</b>\n\n"
                f"Персонаж: {badge_line}\n"
                f"Streak: {streak} дн. подряд 🎯{streak_progress}\n\n"
                f"Вы использовали все сообщения: {messages_used}/{total_limit}.\n\n"
                f"Получите Premium:\n"
                f"⭐ <b>100 Stars</b> — 1 неделя\n"
                f"💵 <b>1.5 USDT (BEP-20)</b> — 1 неделя\n"
                f"📱 <b>Пополнение телефона</b> — 1 неделя (179 ₽)\n\n"
                f"Нажмите кнопку ниже, чтобы продолжить! ⬇️",
                reply_markup=get_main_menu(user_id, username),
                parse_mode="HTML",
            )


@router.message(F.text == "💎 Купить Premium")
@router.message(F.text == "💎 Продлить Premium")
@router.message(Command("buy"))
async def cmd_buy(message: Message):
    """Команда /buy или кнопка"""
    await message.answer(
        "💎 <b>Получи Premium доступ!</b>\n\n"
        "<b>Что входит:</b>\n"
        "✅ Безлимитные сообщения\n"
        "✅ Голосовые + текстовые исправления\n"
        "✅ Разговорная практика\n"
        "✅ Доступ 24/7\n\n"
        "<b>Цены:</b>\n"
        "⭐ <b>100 Stars</b> - 1 неделя (~179 руб)\n"
        "💵 <b>1.5 USDT (BEP-20)</b> - 1 неделя\n"
        "📱 <b>Пополнение телефона</b> - 1 неделя (179 ₽)\n\n"
        "Выбери способ оплаты:",
        reply_markup=get_buy_menu(),
        parse_mode="HTML",
    )


@router.message(F.text == "🧠 Очистить память")
@router.message(Command("reset"))
async def cmd_reset(message: Message):
    """Команда /reset или кнопка"""
    user_id = message.from_user.id
    username = message.from_user.username

    # Сбрасываем историю
    reset_conversation(user_id)

    await message.answer(
        "🧠 <b>Память очищена!</b>\n\n"
        "Я забыл нашу переписку и не помню что мы обсуждали.\n"
        "Давай начнём разговор заново! 🎤\n\n"
        "💡 Сообщения в чате остаются видимыми, но я их больше не помню.",
        reply_markup=get_main_menu(user_id, username),
        parse_mode="HTML",
    )


@router.message(F.text == "❓ Помощь")
@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help или кнопка"""
    user_id = message.from_user.id
    username = message.from_user.username

    text = (
        "📘 <b>Доступные команды:</b>\n\n"
        "📊 <b>Мой статус</b> — Подписка, streak, персонаж\n"
        "🎲 <b>Тема для разговора</b> — Случайная тема + фразы\n"
        "🎯 <b>Проверить уровень</b> — Пройти тест заново\n"
        "💎 <b>Купить Premium</b> — Премиум-доступ\n"
        "🧠 <b>Очистить память</b> — Сбросить историю\n"
        "❓ <b>Помощь</b> — Это меню\n\n"
        "<b>Как это работает:</b>\n"
        "1. Отправляй голосовое или текстовое сообщение на английском\n"
        "2. Я отвечу с исправлениями и голосом\n"
        "3. Практикуйся каждый день — копи streak и получай бонусы!\n\n"
        "<b>Streak-награды:</b>\n"
        "🎁 3 дня — +5 сообщений\n"
        "🎁 7 дней — +10 сообщений\n"
        "🎁 14 дней — +20 сообщений\n"
        "⭐ 30 дней — +1 день Premium\n\n"
        "Нужна помощь? english.tution.bot@gmail.com"
    )

    await message.answer(
        text, parse_mode="HTML", reply_markup=get_main_menu(user_id, username)
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """Показать главное меню"""
    user_id = message.from_user.id
    username = message.from_user.username
    await message.answer(
        "🏠 <b>Главное меню</b>\n\n"
        "Используй кнопки ниже для навигации ⬇️",
        reply_markup=get_main_menu(user_id, username),
        parse_mode="HTML",
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
    levels = get_users_by_level()
    avg_messages = get_average_messages()
    conversion = (active_subs / total_users * 100) if total_users > 0 else 0

    text = (
        "📊 <b>Статистика бота</b>\n"
        f"👥 <b>Всего пользователей:</b> {total_users}\n"
        f"💎 <b>Активных подписок:</b> {active_subs}\n"
        f"📈 <b>Конверсия:</b> {conversion:.1f}%\n"
        "\n📊 <b>Уровни:</b>\n"
    )
    for level in ["A1", "A2", "B1", "B2"]:
        count = levels.get(level, 0)
        text += f"   {level}: {count}\n"
    text += f"\n💬 <b>Среднее сообщений на пользователя:</b> {avg_messages}"

    await message.answer(
        text, parse_mode="HTML", reply_markup=get_main_menu(user_id, username)
    )


@router.message(Command("referral"))
async def cmd_referral(message: Message):
    """Показать реферальный код"""
    user_id = message.from_user.id
    user = get_user(user_id)

    if not user:
        start_kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🚀 Старт", callback_data="go_start")]]
        )
        await message.answer(
            "❌ Пользователь не найден. Нажмите кнопку ниже:",
            reply_markup=start_kb,
        )
        return

    code = user[8] if len(user) > 8 else "Не сгенерирован"
    await message.answer(
        f"🔗 Ваш реферальный код: <code>{code}</code>\n\n"
        f"Поделитесь им с другом — и получите бонус!",
        parse_mode="HTML",
    )


@router.message(F.text == "📢 Пригласить друга")
async def cmd_invite(message: Message):
    """Кнопка 'Пригласить друга' — показывает ссылку на квиз и реферальный код"""
    user_id = message.from_user.id
    username = message.from_user.username
    user = get_user(user_id)

    # Получаем username бота
    bot_info = await message.bot.get_me()
    bot_username = bot_info.username

    quiz_link = f"https://t.me/{bot_username}?start=quiz30"

    # Реферальный код (если есть)
    referral_code = user[8] if user and len(user) > 8 and user[8] else None
    referral_link = f"https://t.me/{bot_username}?start=REF_{referral_code}" if referral_code else None

    text = (
        "📢 <b>Пригласи друга!</b>\n\n"
        "🎓 <b>Ссылка на квиз</b> (5 вопросов):\n"
        f"<code>{quiz_link}</code>\n\n"
        "Отправь эту ссылку друзьям — они пройдут быстрый тест\n"
        "и смогут начать практику английского!\n"
    )

    if referral_link:
        text += (
            f"\n🔗 <b>Твоя реферальная ссылка:</b>\n"
            f"<code>{referral_link}</code>\n\n"
            "Друг получит <b>+50 сообщений</b>, а ты —\n"
            "бонус к подписке!"
        )

    await message.answer(
        text,
        reply_markup=get_main_menu(user_id, username),
        parse_mode="HTML",
    )


@router.message(F.text == "🎯 Проверить уровень")
@router.message(Command("level"))
async def cmd_level(message: Message):
    """Команда /level или кнопка - перепройти тест уровня"""
    user_id = message.from_user.id
    username = message.from_user.username
    user = get_user(user_id)

    if not user:
        start_kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🚀 Старт", callback_data="go_start")]]
        )
        await message.answer(
            "❌ Пользователь не найден. Нажмите кнопку ниже:",
            reply_markup=start_kb,
        )
        return

    # Импортируем функцию здесь, чтобы избежать циклических импортов
    from handlers.onboarding import get_level_selection_keyboard

    text = (
        "🎯 <b>ПРОВЕРКА УРОВНЯ АНГЛИЙСКОГО</b>\n\n"
        "Хотите пройти тест заново?\n"
        "Это поможет адаптировать обучение под ваш текущий уровень.\n\n"
        "Выберите примерный уровень:"
    )

    await message.answer(
        text,
        reply_markup=get_level_selection_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "go_start")
async def cb_go_start(callback: CallbackQuery):
    """Обработчик кнопки Старт из сообщения 'Пользователь не найден'"""
    await callback.answer()
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name

    user = get_user(user_id)
    if not user:
        create_user(user_id, username)

    if not is_onboarding_completed(user_id):
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Начать!", callback_data="start_onboarding")]
            ]
        )
        await callback.message.answer(
            f"Привет, {username}! 👋\n\n"
            "Я твой помощник для практики английского! 🎓\n\n"
            "<b>Что я умею:</b>\n"
            "• Практика разговорной речи (голос и текст)\n"
            "• Мягкие исправления ошибок\n"
            "• Помощь с грамматикой и словами\n"
            "• Адаптация под твой уровень\n\n"
            "Давай начнем с определения твоего уровня!",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    else:
        await callback.message.answer(
            f"Привет, {username}!\n\n"
            "Я твой помощник для практики английского! 🎓\n\n"
            "<b>Как использовать:</b>\n"
            "• Отправляй голосовые или текстовые сообщения на английском\n"
            "• Я помогу тебе практиковать разговорную речь\n"
            "• Мягко исправлю твои ошибки\n"
            "• Спрашивай о словах, грамматике или просто общайся!\n\n"
            "<b>Бесплатно:</b> 25 сообщений\n"
            "<b>Premium:</b> Безлимитный доступ всего за <b>100 Stars</b>/неделю\n\n"
            "Используй кнопки ниже для быстрого доступа! ⬇️",
            reply_markup=get_main_menu(user_id, username),
            parse_mode="HTML",
        )
