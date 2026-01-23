from gtts import gTTS
from pydub import AudioSegment
import os
import tempfile
import re

print("🎤 Инициализация Google TTS (gTTS)...")
print("✅ gTTS готов!")

# gTTS параметры
LANGUAGE = "en"
TLD = "com"  # Top Level Domain - влияет на акцент (com = US accent)
SLOW = False  # Если True - медленная речь для обучения

# СКОРОСТЬ РЕЧИ (через pydub обработку)
# 1.0 = нормальная
# 0.92 = совсем чуть медленнее
# 0.90 = чуть медленнее (оптимально для обучения)
SPEECH_SPEED = 0.92  # Чуть медленнее для лучшего понимания

def remove_emojis(text):
    """Удалить все эмодзи из текста"""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # эмоции
        "\U0001F300-\U0001F5FF"  # символы и пиктограммы
        "\U0001F680-\U0001F6FF"  # транспорт и символы карт
        "\U0001F1E0-\U0001F1FF"  # флаги
        "\U00002702-\U000027B0"  # дингбаты
        "\U000024C2-\U0001F251"  # enclosed characters
        "\U0001F900-\U0001F9FF"  # дополнительные символы и пиктограммы
        "\U0001FA00-\U0001FA6F"  # расширенные символы-A
        "\U0001FA70-\U0001FAFF"  # расширенные символы-B
        "\u2600-\u26FF"          # разное
        "\u2700-\u27BF"          # дингбаты
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)

def text_to_speech(text, output_path=None):
    """
    Преобразовать текст в речь с помощью Google TTS

    Args:
        text: текст для синтеза
        output_path: путь для сохранения (должен быть .wav)

    Returns:
        str: путь к созданному аудио файлу
    """
    try:
        # УБИРАЕМ ЭМОДЗИ перед генерацией голоса
        clean_text = remove_emojis(text)
        clean_text = clean_text.strip()

        if not clean_text:
            print("⚠️ Текст пустой после удаления эмодзи, пропускаю генерацию голоса")
            return None

        print(f"🎤 Генерирую голос через Google TTS: {clean_text[:50]}...")

        # Создаём временный MP3 файл (gTTS генерирует MP3)
        temp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_mp3_path = temp_mp3.name
        temp_mp3.close()

        # Генерируем речь с помощью gTTS
        tts_obj = gTTS(text=clean_text, lang=LANGUAGE, tld=TLD, slow=SLOW)
        tts_obj.save(temp_mp3_path)

        print(f"✅ gTTS сгенерировал MP3")

        # Конвертируем MP3 в WAV и применяем замедление если нужно
        audio = AudioSegment.from_mp3(temp_mp3_path)

        # Если нужно замедлить
        if SPEECH_SPEED != 1.0:
            audio = audio._spawn(
                audio.raw_data,
                overrides={
                    "frame_rate": int(audio.frame_rate * SPEECH_SPEED)
                }
            ).set_frame_rate(audio.frame_rate)
            print(f"🎚 Применена скорость {SPEECH_SPEED}")

        # Если путь не указан - создаём новый временный файл
        if output_path is None:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            output_path = temp_file.name
            temp_file.close()

        # Сохраняем как WAV
        audio.export(output_path, format="wav")

        # Удаляем временный MP3
        try:
            os.remove(temp_mp3_path)
        except:
            pass

        print(f"✅ Аудио создано: {output_path}")
        return output_path

    except Exception as e:
        print(f"❌ TTS error: {e}")
        import traceback
        traceback.print_exc()
        return None

def change_speed(speed):
    """Изменить скорость речи"""
    global SPEECH_SPEED
    SPEECH_SPEED = speed
    print(f"✅ Скорость речи изменена на: {SPEECH_SPEED}")

def change_accent(tld):
    """
    Изменить акцент (через TLD)
    com = US, co.uk = UK, com.au = Australian, co.in = Indian, ca = Canadian
    """
    global TLD
    TLD = tld
    print(f"✅ Акцент изменён на: {tld}")

def enable_slow_mode(enabled=True):
    """Включить/выключить медленный режим (для начинающих)"""
    global SLOW
    SLOW = enabled
    print(f"✅ Медленный режим: {'включен' if enabled else 'выключен'}")

# При импорте показываем настройки
print("📋 Google TTS настройки:")
print(f"  🌍 Язык: {LANGUAGE}")
print(f"  🗣 Акцент: {TLD} (US accent)")
print(f"  🎚 Скорость: {SPEECH_SPEED}")
print(f"  🐌 Медленный режим: {'Да' if SLOW else 'Нет'}")
print("✨ Эмодзи автоматически удаляются перед озвучкой")
print("💡 Доступные акценты: com (US), co.uk (UK), com.au (AU), co.in (IN), ca (CA)")