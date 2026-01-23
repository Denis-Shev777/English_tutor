# Используем slim образ для минимального размера
FROM python:3.11-slim

# Установка только ffmpeg (НЕ НУЖЕН git, все зависимости из PyPI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Копирование requirements.txt для установки зависимостей
COPY requirements.txt .

# Установка Python зависимостей (БЕЗ PyTorch!)
# gTTS + faster-whisper + aiogram = легкий стек без ML фреймворков
RUN pip install --no-cache-dir -r requirements.txt && \
    pip cache purge && \
    rm -rf /root/.cache/pip

# Копирование кода приложения
COPY *.py ./
COPY handlers ./handlers
COPY services ./services

# Создание директории для логов
RUN mkdir -p logs

# Переменные окружения для оптимизации
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Запуск бота
CMD ["python", "main.py"]
