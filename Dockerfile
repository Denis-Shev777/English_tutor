# Используем официальный Python образ
FROM python:3.11-slim

# Установка системных зависимостей для ffmpeg и других библиотек
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование requirements.txt
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование всего проекта
COPY . .

# Создание директории для логов и базы данных
RUN mkdir -p logs

# Запуск бота
CMD ["python", "main.py"]
