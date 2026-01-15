from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (
    get_user,
    create_user,
    reset_conversation,
    get_subscription,
    has_active_subscription,
    WHITELIST_USERNAMES,
    get_total_users,
    get_active_subscriptions,
    FREE_MESSAGE_LIMIT,
    is_onboarding_completed,
    get_referral_code,
    get_level_stats,
    get_user_by_referral_code,
    add_referral,
    give_referral_bonus,
    get_referral_count,
    can_send_referral,
    update_last_referral_sent
)
from handlers.keyboards import get_main_menu, get_buy_menu

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    # Проверяем есть ли реферальный код в команде
    referral_code = None
    if message.text and len(message.text.split()) > 1:
        referral_code = message.text.split()[1]

    # Создаём пользователя если не существует
    user = get_user(user_id)
    is_new_user = user is None

    if not user:
        create_user(user_id, username)

    # Если новый пользователь пришел по реферальной ссылке
    if is_new_user and referral_code:
        referrer = get_user_by_referral_code(referral_code)
        if referrer and referrer[0] != user_id:  # Проверяем что это не сам пользователь
            referrer_id = referrer[0]
            referrer_username = referrer[1]

            # Проверяем может ли реферер получать бонусы (не чаще раза в неделю)
            can_refer, reason = can_send_referral(referrer_id, referrer_username)

            # Добавляем реферала в любом случае
            if add_referral(referrer_id, user_id):
                # Даем новичку бонус всегда (+50 сообщений)
                import sqlite3
                conn = sqlite3.connect("bot.db")
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET message_count = CASE WHEN message_count - 50 < 0 THEN 0 ELSE message_count - 50 END WHERE user_id = ?",
                    (user_id,)
                )
                conn.commit()
                conn.close()

                if can_refer:
                    # Начисляем бонусы рефереру (Premium: +1 день подписки, VIP: ничего)
                    give_referral_bonus(referrer_id, referrer_username, user_id)
                    # Обновляем время последнего реферала
                    update_last_referral_sent(referrer_id)

                    # Определяем сообщение для реферера
                    is_vip = referrer_username in WHITELIST_USERNAMES
                    if is_vip:
                        bonus_text = f"Пользователь @{username} получил <b>+50 бесплатных сообщений</b>!"
                    else:
                        bonus_text = (
                            f"Пользователь @{username} получил <b>+50 бесплатных сообщений</b>!\n"
                            f"🎁 Тебе начислен <b>+1 день Premium подписки</b>!"
                        )

                    # Отправляем уведомление рефереру
                    try:
                        await message.bot.send_message(
                            referrer_id,
                            f"🎉 <b>Новый реферал!</b>\n\n{bonus_text}"
                        )
                    except:
                        pass
                else:
                    # Реферер не может получать бонусы (недавно уже получал)
                    try:
                        await message.bot.send_message(
                            referrer_id,
                            f"ℹ️ Пользователь @{username} присоединился по твоей ссылке и получил <b>+50 бесплатных сообщений</b>!\n\n"
                            f"⏰ {reason}"
                        )
                    except:
                        pass

    # Проверяем онбординг
    if not is_onboarding_completed(user_id):
        # Запускаем онбординг для новых пользователей
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать!", callback_data="start_onboarding")]
        ])

        await message.answer(
            f"Привет, {username}! 👋\n\n"
            "Я твой помощник для практики английского! 🎓\n\n"
            "<b>Что я умею:</b>\n"
            "• Практика разговорной речи (голос и текст)\n"
            "• Мягкие исправления ошибок\n"
            "• Помощь с грамматикой и словами\n"
            "• Адаптация под твой уровень\n\n"
            "Давай начнем с определения твоего уровня!",
            reply_markup=keyboard
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
        "<b>Premium:</b> Безлимитный доступ всего за 100 Stars/неделю\n\n"
        "Используй кнопки ниже для быстрого доступа! ⬇️",
        reply_markup=get_main_menu(user_id, username)
    )

@router.message(F.text == "📊 Мой статус")
@router.message(Command("status"))
async def cmd_status(message: Message):
    """Команда /status или кнопка"""
    user_id = message.from_user.id
    username = message.from_user.username
    user = get_user(user_id)
    
    if not user:
        await message.answer("❌ User not found. Please use /start first.")
        return
    
    # Белый список по username
    if username and username in WHITELIST_USERNAMES:
        referral_code = get_referral_code(user_id) or "N/A"
        referral_count = get_referral_count(user_id)

        # Получаем BOT_USERNAME из переменных окружения
        import os
        bot_username = os.getenv("BOT_USERNAME", "English_Tutor_bot")
        referral_link = f"https://t.me/{bot_username}?start={referral_code}"

        # Проверяем когда можно следующего реферала
        can_refer, reason = can_send_referral(user_id, username)
        ref_status = "✅ Можешь приглашать!" if can_refer else f"⏰ {reason}"

        # Кнопка "Пригласить друга"
        invite_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Пригласить друга", url=f"https://t.me/share/url?url={referral_link}&text=Привет! Попробуй этого бота для изучения английского 🎓")]
        ])

        await message.answer(
            "⭐ <b>VIP Статус</b>\n\n"
            "У вас безлимитный доступ!\n"
            "Использовано сообщений: ∞\n"
            "Подписка: Lifetime Premium 💎\n\n"
            f"👥 <b>Приглашено друзей:</b> {referral_count}\n"
            f"🎁 <b>Реферальная программа:</b>\n"
            f"• Друг получает: <b>+50 бесплатных сообщений</b>\n"
            f"• Ограничение: не чаще 1 раза в неделю\n"
            f"• Статус: {ref_status}\n\n"
            f"<b>Твоя ссылка:</b>\n<code>{referral_link}</code>",
            reply_markup=invite_keyboard
        )
        return
    
    # Проверяем подписку
    subscription = get_subscription(user_id)
    
    if has_active_subscription(user_id) and subscription:
        expires = datetime.fromisoformat(subscription[1])
        time_left = expires - datetime.now()

        # Форматируем оставшееся время
        if time_left.days > 0:
            time_left_str = f"{time_left.days} дней" if time_left.days > 1 else "1 день"
        else:
            hours_left = time_left.seconds // 3600
            time_left_str = f"{hours_left} часов" if hours_left > 1 else "1 час"

        referral_code = get_referral_code(user_id) or "N/A"
        referral_count = get_referral_count(user_id)

        # Получаем BOT_USERNAME из переменных окружения
        import os
        bot_username = os.getenv("BOT_USERNAME", "English_Tutor_bot")
        referral_link = f"https://t.me/{bot_username}?start={referral_code}"

        # Проверяем когда можно следующего реферала
        can_refer, reason = can_send_referral(user_id, username)
        ref_status = "✅ Можешь приглашать!" if can_refer else f"⏰ {reason}"

        # Кнопка "Пригласить друга"
        invite_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Пригласить друга", url=f"https://t.me/share/url?url={referral_link}&text=Привет! Попробуй этого бота для изучения английского 🎓")]
        ])

        await message.answer(
            f"✅ <b>Premium Активен</b>\n\n"
            f"Статус: Premium 💎\n"
            f"Истекает: {expires.strftime('%Y-%m-%d %H:%M')}\n"
            f"Осталось: {time_left_str}\n\n"
            f"👥 <b>Приглашено друзей:</b> {referral_count}\n"
            f"🎁 <b>Реферальная программа:</b>\n"
            f"• Ты получаешь: <b>+1 день подписки</b>\n"
            f"• Друг получает: <b>+50 бесплатных сообщений</b>\n"
            f"• Ограничение: не чаще 1 раза в неделю\n"
            f"• Статус: {ref_status}\n\n"
            f"<b>Твоя ссылка:</b>\n<code>{referral_link}</code>",
            reply_markup=invite_keyboard
        )
    else:
        messages_used = user[2]
        messages_left = FREE_MESSAGE_LIMIT - messages_used

        if messages_left > 0:
            await message.answer(
                f"📊 <b>Бесплатный тариф</b>\n\n"
                f"Использовано: {messages_used}/25\n"
                f"Осталось: {messages_left}\n\n"
                f"🎁 <b>Реферальная программа</b> доступна только для Premium и VIP пользователей!\n\n"
                f"Хочешь безлимит и возможность приглашать друзей?\n"
                f"Premium всего <b>100 Stars/неделю</b>!",
                reply_markup=get_main_menu(user_id, username)
            )
        else:
            await message.answer(
                f"🚫 <b>Бесплатные сообщения закончились</b>\n\n"
                f"Вы использовали все 25 бесплатных сообщений.\n\n"
                f"<b>Получи Premium:</b>\n"
                f"⭐ <b>100 Stars</b> - 1 неделя\n"
                f"💵 <b>1.5 USDT (BEP-20)</b> - 1 неделя\n\n"
                f"<b>Бонус для Premium:</b>\n"
                f"🎁 Приглашай друзей и получай +1 день подписки за каждого!",
                reply_markup=get_main_menu(user_id, username)
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
        "💵 <b>1.5 USDT (BEP-20)</b> - 1 неделя\n\n"
        "Выбери способ оплаты:",
        reply_markup=get_buy_menu()
    )

@router.message(F.text == "🧠 Очистить память")  # ← ИЗМЕНИЛИ
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
        reply_markup=get_main_menu(user_id, username)
    )

@router.message(F.text == "❓ Помощь")
@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help или кнопка"""
    user_id = message.from_user.id
    username = message.from_user.username
    await message.answer(
        "📚 <b>Доступные команды:</b>\n\n"
        "<b>📊 Мой статус</b> - Проверить подписку\n"
        "<b>💎 Купить Premium</b> - Получить премиум доступ\n"
        "<b>🧠 Очистить память</b> - Бот забывает переписку\n"
        "<b>❓ Помощь</b> - Показать эту справку\n\n"
        "<b>Как это работает:</b>\n"
        "1. Отправляй голос или текст на английском\n"
        "2. Я отвечу с исправлениями и голосом\n"
        "3. Практикуйся естественно и улучшайся!\n\n"
        "Нужна помощь? Пиши english.tution.bot@gmail.com",
        reply_markup=get_main_menu(user_id, username)
    )

@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """Показать главное меню"""
    user_id = message.from_user.id
    username = message.from_user.username
    await message.answer(
        "🏠 <b>Главное меню</b>\n\n"
        "Используй кнопки ниже для навигации ⬇️",
        reply_markup=get_main_menu(user_id, username)
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
    level_stats = get_level_stats()

    conversion = (active_subs/total_users*100) if total_users > 0 else 0

    # Форматируем статистику по уровням
    level_text = ""
    if level_stats:
        for level, count in level_stats:
            level_text += f"{level}: {count} чел.\n"
    else:
        level_text = "Нет данных\n"

    await message.answer(
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 <b>Всего пользователей:</b> {total_users}\n"
        f"💎 <b>Активные подписки:</b> {active_subs}\n"
        f"📈 <b>Конверсия:</b> {conversion:.1f}%\n\n"
        f"📚 <b>По уровням:</b>\n{level_text}",
        reply_markup=get_main_menu(user_id, username)
    )