from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from database import has_active_subscription
import os
from dotenv import load_dotenv

load_dotenv()
WHITELIST_USERNAMES = os.getenv("WHITELIST_USERNAMES", "").split(",")


def get_suggested_phrases_keyboard():
    """Клавиатура с готовыми фразами для начинающих"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Hello!", callback_data="phrase_hello")],
            [
                InlineKeyboardButton(
                    text="How are you?", callback_data="phrase_how_are_you"
                )
            ],
            [
                InlineKeyboardButton(
                    text="I am fine, thank you", callback_data="phrase_fine_thank_you"
                )
            ],
            [
                InlineKeyboardButton(
                    text="What is your name?", callback_data="phrase_name"
                )
            ],
            [InlineKeyboardButton(text="Goodbye!", callback_data="phrase_goodbye")],
        ]
    )


def get_main_menu(user_id=None, username=None):
    """Главное меню в зависимости от статуса"""
    # VIP пользователи
    if username and username in WHITELIST_USERNAMES:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="📊 Мой статус"),
                    KeyboardButton(text="📈 Статистика"),
                ],
                [
                    KeyboardButton(text="🎲 Тема для разговора"),
                    KeyboardButton(text="🎯 Проверить уровень"),
                ],
                [
                    KeyboardButton(text="📢 Пригласить друга"),
                    KeyboardButton(text="🧠 Очистить память"),
                ],
                [
                    KeyboardButton(text="📣 Рассылка"),
                    KeyboardButton(text="❓ Помощь"),
                ],
            ],
            resize_keyboard=True,
            persistent=True,
        )
    # Premium пользователи
    elif user_id and has_active_subscription(user_id):
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="📊 Мой статус"),
                    KeyboardButton(text="💎 Продлить Premium"),
                ],
                [
                    KeyboardButton(text="🎲 Тема для разговора"),
                    KeyboardButton(text="🎯 Проверить уровень"),
                ],
                [
                    KeyboardButton(text="📢 Пригласить друга"),
                    KeyboardButton(text="🧠 Очистить память"),
                ],
                [
                    KeyboardButton(text="❓ Помощь"),
                ],
            ],
            resize_keyboard=True,
            persistent=True,
        )
    # FREE пользователи
    else:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="📊 Мой статус"),
                    KeyboardButton(text="💎 Купить Premium"),
                ],
                [
                    KeyboardButton(text="🎲 Тема для разговора"),
                    KeyboardButton(text="🎯 Проверить уровень"),
                ],
                [
                    KeyboardButton(text="📢 Пригласить друга"),
                    KeyboardButton(text="🧠 Очистить память"),
                ],
                [
                    KeyboardButton(text="❓ Помощь"),
                ],
            ],
            resize_keyboard=True,
            persistent=True,
        )
    return keyboard


def get_buy_menu():
    """Меню выбора способа оплаты"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⭐ Telegram Stars (100)", callback_data="pay_stars"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💵 USDT BEP-20 (1.5)", callback_data="pay_usdt"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📱 Пополнение телефона (179 ₽)", callback_data="pay_phone"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❓ Как купить Stars?", callback_data="how_to_buy_stars"
                )
            ],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ]
    )
    return keyboard


def get_stars_help_menu():
    """Меню после инструкции по покупке Stars"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Купить Stars", callback_data="pay_stars")],
            [
                InlineKeyboardButton(
                    text="💵 USDT вместо Stars", callback_data="pay_usdt"
                )
            ],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ]
    )
    return keyboard
