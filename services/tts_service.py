from TTS.api import TTS
from pydub import AudioSegment
import os
import tempfile
import re

print("🎤 Загрузка Coqui TTS модели...")

tts = TTS(model_name="tts_models/en/vctk/vits", gpu=False)

print("✅ Coqui TTS готов!")

SPEAKER = "p260"  # Профессиональный женский голос

# СКОРОСТЬ РЕЧИ для обучения
# 1.0 = нормальная
# 0.92 = совсем чуть медленнее (почти не меняет тон)
# 0.90 = чуть медленнее (оптимально)
# 0.85 = медленнее (начинает меняться тон)
SPEECH_SPEED = 0.89  # Оптимальный баланс!

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
    Преобразовать текст в речь с небольшим замедлением
    
    Args:
        text: текст для синтеза
        output_path: путь для сохранения
    
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
        
        # Создаём временный файл для оригинального аудио
        temp_original = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_original_path = temp_original.name
        temp_original.close()
        
        print(f"🎤 Генерирую голос (без эмодзи): {clean_text[:50]}...")
        
        # Генерируем речь БЕЗ эмодзи
        tts.tts_to_file(
            text=clean_text,
            file_path=temp_original_path,
            speaker=SPEAKER
        )
        
        # Если скорость = 1.0, не обрабатываем
        if SPEECH_SPEED == 1.0:
            if output_path:
                import shutil
                shutil.copy(temp_original_path, output_path)
                os.remove(temp_original_path)
                print(f"✅ Аудио создано (нормальная скорость): {output_path}")
                return output_path
            else:
                print(f"✅ Аудио создано (нормальная скорость): {temp_original_path}")
                return temp_original_path
        
        # Загружаем аудио
        audio = AudioSegment.from_wav(temp_original_path)
        
        # Замедляем аудио (небольшое изменение тона допустимо)
        slowed_audio = audio._spawn(
            audio.raw_data,
            overrides={
                "frame_rate": int(audio.frame_rate * SPEECH_SPEED)
            }
        ).set_frame_rate(audio.frame_rate)
        
        # Если путь не указан - создаём новый временный файл
        if output_path is None:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            output_path = temp_file.name
            temp_file.close()
        
        # Сохраняем замедленное аудио
        slowed_audio.export(output_path, format="wav")
        
        # Удаляем временный оригинал
        try:
            os.remove(temp_original_path)
        except:
            pass
        
        print(f"✅ Аудио создано со скоростью {SPEECH_SPEED}: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ TTS error: {e}")
        import traceback
        traceback.print_exc()
        return None

def change_speaker(speaker_id):
    """Изменить голос"""
    global SPEAKER
    SPEAKER = speaker_id
    print(f"✅ Голос изменён на: {SPEAKER}")

def change_speed(speed):
    """Изменить скорость речи"""
    global SPEECH_SPEED
    SPEECH_SPEED = speed
    print(f"✅ Скорость речи изменена на: {SPEECH_SPEED}")

def list_female_speakers():
    """Список проверенных женских голосов"""
    return {
        'p225': 'Молодой, мягкий',
        'p226': 'Средний возраст',
        'p228': 'Энергичный',
        'p231': 'Спокойный',
        'p233': 'Уверенный',
        'p236': 'Приятный',
        'p244': 'Профессиональный (текущий)',
        'p248': 'Дружелюбный',
        'p250': 'Нейтральный',
        'p253': 'Теплый',
        'p257': 'Энергичный 2',
        'p258': 'Нейтральный 2',
    }

# При импорте показываем настройки
print("📋 Доступные женские голоса:")
for speaker, description in list_female_speakers().items():
    marker = "⭐" if speaker == SPEAKER else "  "
    print(f"{marker} {speaker}: {description}")

print(f"\n🎚 Скорость речи: {SPEECH_SPEED}")
print("✨ Эмодзи автоматически удаляются перед озвучкой")
print("💡 Рекомендации: 0.90-0.95 = оптимально, 1.0 = нормально")