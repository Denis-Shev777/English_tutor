from aiogram import Router, F
from aiogram.types import Message, LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import activate_subscription, save_payment, get_user, set_referral_code
from handlers.keyboards import get_main_menu, get_buy_menu, get_stars_help_menu

router = Router()

STARS_PRICE = 100
USDT_PRICE = 1.5
USDT_WALLET = os.getenv("USDT_WALLET_ADDRESS", "")
PHONE_NUMBER = "+79298301702"
PHONE_PRICE = "179 ₽"

def generate_referral_code():
    """6-символьный реферальный код (A-Z0-9)"""
    import random, string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@router.callback_query(F.data == "pay_stars")
async def callback_pay_stars(callback: CallbackQuery):
    """Оплата через Stars"""
    await callback.answer()
    user_id = callback.from_user.id
    
    prices = [LabeledPrice(label="Premium на 1 неделю", amount=STARS_PRICE)]
    
    await callback.message.answer_invoice(
        title="English Tutor Premium",
        description="Безлимитная практика на 1 неделю с голосовыми исправлениями и AI учителем",
        prices=prices,
        provider_token="",
        payload=f"premium_week_{user_id}",
        currency="XTR"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Как купить Stars?", callback_data="how_to_buy_stars")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.answer(
        "Нужна помощь с покупкой Telegram Stars?",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "pay_usdt")
async def callback_pay_usdt(callback: CallbackQuery):
    """Оплата через USDT"""
    await callback.answer()
    user_id = callback.from_user.id
    username = callback.from_user.username
    
    if not USDT_WALLET:
        await callback.message.answer(
            "Оплата USDT временно недоступна.\n"
            "Используй Telegram Stars.",
            reply_markup=get_main_menu(user_id, username)
        )
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Скопировать адрес", callback_data="copy_wallet")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    text = (
        "Оплата USDT BEP-20\n\n"
        "Цена: 1.5 USDT\n"
        "Сеть: BEP-20 (Binance Smart Chain)\n\n"
        "Инструкция:\n"
        "1. Отправь ровно 1.5 USDT на адрес ниже\n"
        "2. Используй сеть BEP-20 (Binance Smart Chain)\n"
        "3. После оплаты отправь хеш транзакции (TxID) в @Den_Shev_007\n"
        "4. Подписка активируется в течение 1 часа\n\n"
        "Важно:\n"
        "- Неправильная сеть = потеря средств!\n"
        "- Отправляй только USDT (BEP-20), не BNB или другие токены\n"
        "- Сохрани хеш транзакции\n\n"
        "Адрес кошелька ниже:"
    )
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.message.answer(f"`{USDT_WALLET}`", parse_mode="Markdown")

@router.callback_query(F.data == "copy_wallet")
async def copy_wallet_address(callback: CallbackQuery):
    """Копирование адреса кошелька"""
    if USDT_WALLET:
        await callback.answer(f"Адрес скопирован: {USDT_WALLET}", show_alert=True)
    else:
        await callback.answer("Адрес не настроен", show_alert=True)

@router.callback_query(F.data == "pay_phone")
async def callback_pay_phone(callback: CallbackQuery):
    """Оплата через пополнение телефона"""
    await callback.answer()
    user_id = callback.from_user.id

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я пополнил", callback_data="phone_paid")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])

    text = (
        "📱 <b>Оплата пополнением телефона</b>\n\n"
        f"<b>Сумма:</b> {PHONE_PRICE}\n"
        f"<b>Номер:</b> <code>{PHONE_NUMBER}</code>\n\n"
        "<b>Инструкция:</b>\n"
        "1. Пополни баланс номера выше на 179 ₽\n"
        "2. Через банковское приложение, терминал или онлайн\n"
        "3. Нажми кнопку <b>«Я пополнил»</b>\n"
        "4. Подписка активируется в течение 1 часа\n\n"
        "💡 Нажми на номер, чтобы скопировать"
    )

    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "phone_paid")
async def callback_phone_paid(callback: CallbackQuery):
    """Пользователь нажал 'Я пополнил'"""
    await callback.answer()
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name

    # Уведомляем админа
    admin_usernames = os.getenv("WHITELIST_USERNAMES", "").split(",")
    for admin_username in admin_usernames:
        admin_username = admin_username.strip()
        if admin_username:
            try:
                # Ищем admin user_id в базе по username
                from database import get_user_id_by_username
                admin_id = get_user_id_by_username(admin_username)
                if admin_id:
                    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="✅ Подтвердить оплату",
                            callback_data=f"confirm_phone_{user_id}"
                        )],
                        [InlineKeyboardButton(
                            text="❌ Отклонить",
                            callback_data=f"reject_phone_{user_id}"
                        )]
                    ])
                    await callback.bot.send_message(
                        admin_id,
                        f"📱 <b>Заявка на оплату через телефон</b>\n\n"
                        f"Пользователь: @{username} (ID: {user_id})\n"
                        f"Сумма: {PHONE_PRICE}\n"
                        f"Номер: {PHONE_NUMBER}\n\n"
                        f"Проверь пополнение и подтверди.",
                        reply_markup=admin_kb,
                        parse_mode="HTML"
                    )
            except Exception:
                pass

    await callback.message.answer(
        "✅ <b>Заявка отправлена!</b>\n\n"
        "Администратор проверит пополнение и активирует\n"
        "Premium в течение 1 часа.\n\n"
        "Спасибо за оплату!",
        reply_markup=get_main_menu(user_id, username),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("confirm_phone_"))
async def confirm_phone_payment(callback: CallbackQuery):
    """Админ подтверждает оплату через телефон"""
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])

    # Активируем подписку
    expires = activate_subscription(user_id, duration_days=7)

    # Сохраняем платёж
    save_payment(
        user_id=user_id,
        payment_method="phone_topup",
        amount=179,
        currency="RUB",
        transaction_id=f"phone_{user_id}_{int(__import__('time').time())}",
        status="completed"
    )

    # Генерируем реферальный код
    referral_code = generate_referral_code()
    set_referral_code(user_id, referral_code)

    # Уведомляем пользователя
    try:
        await callback.bot.send_message(
            user_id,
            f"🎉 <b>Premium активирован!</b>\n\n"
            f"Оплата через пополнение телефона подтверждена.\n"
            f"Подписка действует до: {expires.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"Твой реферальный код: <code>{referral_code}</code>\n"
            f"Пригласи друга — получи +1 день Premium!",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.message.edit_text(
        f"✅ Оплата подтверждена для пользователя {user_id}.\n"
        f"Premium до: {expires.strftime('%Y-%m-%d %H:%M')}"
    )


@router.callback_query(F.data.startswith("reject_phone_"))
async def reject_phone_payment(callback: CallbackQuery):
    """Админ отклоняет оплату"""
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])

    try:
        await callback.bot.send_message(
            user_id,
            "❌ <b>Оплата не подтверждена</b>\n\n"
            "Пополнение не найдено. Если ты уже пополнил —\n"
            "напиши @Den_Shev_007 с чеком/скриншотом.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.message.edit_text(
        f"❌ Оплата отклонена для пользователя {user_id}."
    )


@router.callback_query(F.data == "how_to_buy_stars")
async def show_stars_guide(callback: CallbackQuery):
    """Инструкция по покупке Stars"""
    text = (
        "КАК КУПИТЬ TELEGRAM STARS\n\n"
        "Пошаговая инструкция:\n\n"
        "1. Открой Настройки Telegram (три полоски)\n\n"
        "2. Прокрути вниз до кнопки 'Мои звезды' (My Stars)\n\n"
        "3. Нажми на 'Мои звезды'\n\n"
        "4. Нажми кнопку 'Купить звезды'\n\n"
        "5. Выбери количество:\n"
        "   - 100 звезд = 179 руб\n"
        "   - 150 звезд = 259 руб\n"
        "   - 250 звезд = 424 руб\n\n"
        "6. Выбери способ оплаты:\n"
        "   - Банковская карта (РФ карты работают!)\n"
        "   - СберПей\n\n"
        "7. Подтверди оплату\n\n"
        "Готово! Stars появятся мгновенно!\n\n"
        "Если не получается купить Stars:\n"
        "- Используй USDT вместо Stars\n\n"
        "После покупки Stars вернись и нажми кнопку ниже!"
    )
    
    await callback.answer()
    await callback.message.answer(text, reply_markup=get_stars_help_menu())

@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    """Вернуться в главное меню"""
    await callback.answer()
    user_id = callback.from_user.id
    username = callback.from_user.username
    
    await callback.message.answer(
        "Главное меню\n\n"
        "Выбери действие с помощью кнопок ниже:",
        reply_markup=get_main_menu(user_id, username)
    )
    try:
        await callback.message.delete()
    except:
        pass

@router.message(Command("buy_stars"))
async def cmd_buy_stars(message: Message):
    """Оплата через Telegram Stars"""
    user_id = message.from_user.id
    
    prices = [LabeledPrice(label="Premium на 1 неделю", amount=STARS_PRICE)]
    
    await message.answer_invoice(
        title="English Tutor Premium",
        description="Безлимитная практика на 1 неделю с голосовыми исправлениями и AI учителем",
        prices=prices,
        provider_token="",
        payload=f"premium_week_{user_id}",
        currency="XTR"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Как купить Stars?", callback_data="how_to_buy_stars")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await message.answer(
        "Нужна помощь с покупкой Telegram Stars?",
        reply_markup=keyboard
    )

@router.message(Command("buy_usdt"))
async def cmd_buy_usdt(message: Message):
    """Оплата через USDT BEP-20"""
    user_id = message.from_user.id
    username = message.from_user.username
    
    if not USDT_WALLET:
        await message.answer(
            "Оплата USDT временно недоступна.\n"
            "Используй /buy_stars для оплаты через Telegram Stars.",
            reply_markup=get_main_menu(user_id, username)
        )
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Скопировать адрес", callback_data="copy_wallet")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    text = (
        "Оплата USDT BEP-20\n\n"
        "Цена: 1.5 USDT\n"
        "Сеть: BEP-20 (Binance Smart Chain)\n\n"
        "Инструкция:\n"
        "1. Отправь ровно 1.5 USDT на адрес ниже\n"
        "2. Используй сеть BEP-20 (Binance Smart Chain)\n"
        "3. После оплаты отправь хеш транзакции (TxID) в @Den_Shev_007\n"
        "4. Подписка активируется в течение 1 часа\n\n"
        "Важно:\n"
        "- Неправильная сеть = потеря средств!\n"
        "- Отправляй только USDT (BEP-20), не BNB или другие токены\n"
        "- Сохрани хеш транзакции\n\n"
        "Адрес кошелька ниже:"
    )
    
    await message.answer(text, reply_markup=keyboard)
    await message.answer(f"`{USDT_WALLET}`", parse_mode="Markdown")

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    """Обработка pre-checkout"""
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    """Обработка успешной оплаты Stars"""
    user_id = message.from_user.id
    username = message.from_user.username
    payment_info = message.successful_payment
    
    # Активируем подписку
    expires = activate_subscription(user_id, duration_days=7)
    
    # Сохраняем платёж
    save_payment(
        user_id=user_id,
        payment_method="telegram_stars",
        amount=STARS_PRICE,
        currency="XTR",
        transaction_id=payment_info.telegram_payment_charge_id,
        status="completed"
    )
    
    # === ГЕНЕРИРУЕМ И СОХРАНЯЕМ РЕФЕРАЛЬНЫЙ КОД ===
    referral_code = generate_referral_code()
    set_referral_code(user_id, referral_code)

# === ОДНО СООБЩЕНИЕ ===
    await message.answer(
        f"Оплата прошла успешно!\n\n"
        f"Твоя Premium подписка активна!\n"
        f"Действует до: {expires.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"🎉 Твой реферальный код: `{referral_code}`\n"
        f"Пригласи друга — и получи +1 день Premium!\n\n"
        f"Используй /status для проверки подписки.",
        reply_markup=get_main_menu(user_id, username)
    )