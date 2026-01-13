"""
Централизованная система логирования для English Tutor Bot
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Создаем директорию для логов если её нет
if not os.path.exists('logs'):
    os.makedirs('logs')

# Настраиваем форматирование
formatter = logging.Formatter(
    '[%(asctime)s] %(levelname)-8s [%(name)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Создаем главный логгер
logger = logging.getLogger('english_tutor')
logger.setLevel(logging.INFO)

# Обработчик для файла (с ротацией)
file_handler = RotatingFileHandler(
    'logs/bot.log',
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Обработчик для ошибок (отдельный файл)
error_handler = RotatingFileHandler(
    'logs/errors.log',
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5,
    encoding='utf-8'
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)

# Обработчик для консоли
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    '%(levelname)-8s [%(name)s] - %(message)s'
)
console_handler.setFormatter(console_formatter)

# Добавляем обработчики
logger.addHandler(file_handler)
logger.addHandler(error_handler)
logger.addHandler(console_handler)

# Логгеры для отдельных модулей
def get_logger(name: str):
    """Получить логгер для конкретного модуля"""
    return logging.getLogger(f'english_tutor.{name}')
