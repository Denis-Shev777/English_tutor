# Multi-stage build для уменьшения размера образа
FROM python:3.11-slim as builder

# Установка системных зависимостей только для сборки
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копирование requirements.txt
COPY requirements.txt .

# Установка зависимостей в отдельную директорию
RUN pip install --no-cache-dir --target=/app/dependencies \
    torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir --target=/app/dependencies \
    -r requirements.txt

# Финальный образ
FROM python:3.11-slim

# Установка только runtime зависимостей (ffmpeg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Копирование установленных зависимостей из builder
COPY --from=builder /app/dependencies /usr/local/lib/python3.11/site-packages

# Копирование только необходимых файлов проекта
COPY *.py ./
COPY handlers ./handlers
COPY services ./services
COPY .env* ./

# Создание директории для логов и базы данных
RUN mkdir -p logs

# Переменные окружения для оптимизации
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Запуск бота
CMD ["python", "main.py"]
