from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
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
            "**Что я умею:**\n"
            "• Практика разговорной речи (голос и текст)\n"
            "• Мягкие исправления ошибок\n"
            "• Помощь с грамматикой и словами\n"
            "• Адаптация под твой уровень\n\n"
            "Давай начнем с определения твоего уровня!",
            reply_markup=keyboard,
        )
        return

    # Обычное приветствие для пользователей с онбордингом
    await message.answer(
        f"Привет, {username}!\n\n"
        "Я твой помощник для практики английского! 🎓\n\n"
        "**Как использовать:**\n"
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
        await message.answer("❌ Пользователь не найден. Используйте /start.")
        return

    # Получаем streak (8-й элемент)
    streak = user[7] if len(user) > 7 else 0

    # Белый список по username
    if username and username in WHITELIST_USERNAMES:
        referral_code = user[8] if len(user) > 8 else "Не сгенерирован"
        await message.answer(
            "⭐ **VIP Статус**\n\n"
            "У вас неограниченный доступ!\n"
            "Использовано сообщений: ∞\n"
            "Подписка: Пожизненный Premium 💎\n"
            f"Реферальный код: `{referral_code}`",
            reply_markup=get_main_menu(user_id, username),
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
            f"✅ **Premium активен**\n\n"
            f"Статус: Premium 💎\n"
            f"Streak: {streak} {'день' if streak == 1 else 'дня' if 2 <= streak <= 4 else 'дней'} подряд 🎯\n"
            f"Истекает: {expires.strftime('%Y-%m-%d %H:%M')}\n"
            f"{time_info}\n"
            f"Реферальный код: `{referral_code}`\n\n"
            f"Продолжайте в том же духе!",
            reply_markup=get_main_menu(user_id, username),
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
                f"📊 **Бесплатный уровень**\n\n"
                f"{bonus_line}"
                f"Использовано сообщений: {messages_used}/{total_limit}\n"
                f"Осталось: {messages_left}\n"
                f"Streak: {streak} {'день' if streak == 1 else 'дня' if 2 <= streak <= 4 else 'дней'} подряд 🎯\n\n"
                f"Хотите неограниченный доступ?\n"
                f"Получите Premium всего за <b>100 Stars</b>/неделя!\n\n"
                f"Нажмите кнопку ниже, чтобы обновить! ⬇️",
                reply_markup=get_main_menu(user_id, username),
                parse_mode="HTML",
            )
        else:
            await message.answer(
                f"🚫 **Сообщения закончились**\n\n"
                f"Вы использовали все доступные сообщения: {messages_used}/{total_limit}.\n"
                f"Streak: {streak} {'день' if streak == 1 else 'дня' if 2 <= streak <= 4 else 'дней'} подряд 🎯\n\n"
                f"Получите Premium:\n"
                f"⭐ <b>100 Stars</b> — 1 неделя\n"
                f"💵 <b>1.5 USDT (BEP-20)</b> — 1 неделя\n\n"
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
        "💎 **Получи Premium доступ!**\n\n"
        "**Что входит:**\n"
        "✅ Безлимитные сообщения\n"
        "✅ Голосовые + текстовые исправления\n"
        "✅ Разговорная практика\n"
        "✅ Доступ 24/7\n\n"
        "**Цены:**\n"
        "⭐ <b>100 Stars</b> - 1 неделя (~179 руб)\n"
        "💵 <b>1.5 USDT (BEP-20)</b> - 1 неделя\n\n"
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
        "🧠 **Память очищена!**\n\n"
        "Я забыл нашу переписку и не помню что мы обсуждали.\n"
        "Давай начнём разговор заново! 🎤\n\n"
        "💡 Сообщения в чате остаются видимыми, но я их больше не помню.",
        reply_markup=get_main_menu(user_id, username),
    )


@router.message(F.text == "❓ Помощь")
@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help или кнопка"""
    user_id = message.from_user.id
    username = message.from_user.username

    text = (
        "📘 <b>Доступные команды:</b>\n"
        "📊 <b>Мой статус</b> — Проверить подписку\n"
        "🎯 <b>Проверить уровень</b> — Пройти тест уровня заново\n"
        "💎 <b>Купить Premium</b> — Получить премиум-доступ\n"
        "🧠 <b>Очистить память</b> — Бот забывает историю разговора\n"
        "❓ <b>Помощь</b> — Показать это меню\n\n"
        "<b>Как это работает:</b>\n"
        "1. Отправляй голосовое или текстовое сообщение на английском\n"
        "2. Я отвечу с исправлениями и голосом\n"
        "3. Практикуйся естественно и улучшайся!\n\n"
        "Нужна помощь? Напишите нам: english.tution.bot@gmail.com"
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
        "🏠 **Главное меню**\n\n" "Используй кнопки ниже для навигации ⬇️",
        reply_markup=get_main_menu(user_id, username),
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
        await message.answer("❌ Пользователь не найден. Используйте /start.")
        return

    code = user[8] if len(user) > 8 else "Не сгенерирован"
    await message.answer(
        f"🔗 Ваш реферальный код: `{code}`\n\n"
        f"Поделитесь им с другом — и получите бонус!"
    )


@router.message(F.text == "🎯 Проверить уровень")
@router.message(Command("level"))
async def cmd_level(message: Message):
    """Команда /level или кнопка - перепройти тест уровня"""
    user_id = message.from_user.id
    username = message.from_user.username
    user = get_user(user_id)

    if not user:
        await message.answer("❌ Пользователь не найден. Используйте /start.")
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
