# Используем slim образ для минимального размера
FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Копирование requirements.txt ПЕРВЫМ для кеширования слоя
COPY requirements.txt .

# Установка зависимостей по частям для лучшего кеширования
# 1. Сначала PyTorch (самый тяжелый)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 2. Потом остальные зависимости
RUN pip install --no-cache-dir -r requirements.txt

# 3. Очистка pip кеша
RUN pip cache purge && rm -rf /root/.cache/pip

# Копирование кода проекта ПОСЛЕ установки зависимостей
COPY *.py ./
COPY handlers ./handlers
COPY services ./services

# Создание необходимых директорий
RUN mkdir -p logs

# Оптимизация Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Запуск бота
CMD ["python", "main.py"]
