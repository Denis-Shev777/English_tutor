import whisper
import os
import re
from pydub import AudioSegment
import tempfile

print("🎧 Загрузка Whisper модели...")

# Используем модель "medium" - лучшая точность распознавания
# base: быстро, но низкое качество
# small: средне, но всё ещё ошибки в автоопределении языка
# medium: медленнее, но высокое качество и точное определение языка
model = whisper.load_model("medium")

print("✅ Whisper готов!")

def clean_non_english_chars(text):
    """
    Удаляет неанглийские символы (китайские, арабские и т.д.)
    Оставляет только: латиницу, цифры, знаки препинания, пробелы
    """
    # Разрешенные символы: латиница, цифры, основная пунктуация, пробелы
    cleaned = re.sub(r'[^a-zA-Z0-9\s\'\"\.,!?\-]', '', text)
    # Убираем множественные пробелы
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def transcribe_audio(audio_file_path):
    """
    Распознать речь из аудио файла
    
    Args:
        audio_file_path: путь к аудио файлу
    
    Returns:
        str: распознанный текст или None при ошибке
    """
    wav_path = None
    
    try:
        print(f"🎧 Получен файл: {audio_file_path}")
        
        # Конвертируем через pydub в WAV 16kHz mono (то что нужно Whisper)
        print("🔄 Конвертирую аудио...")
        audio = AudioSegment.from_file(audio_file_path)
        
        # Информация об аудио
        duration = len(audio) / 1000.0  # в секундах
        print(f"📊 Длительность: {duration:.2f} сек, Каналы: {audio.channels}, Sample rate: {audio.frame_rate}")
        
        # Увеличиваем громкость на 10 дБ (на случай тихого аудио)
        audio = audio + 10
        
        # Whisper требует: 16kHz, mono
        audio = audio.set_frame_rate(16000).set_channels(1)
        
        # Создаём временный WAV файл
        temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        wav_path = temp_wav.name
        temp_wav.close()
        
        # Экспортируем в WAV
        audio.export(wav_path, format="wav")
        print(f"✅ Конвертировано: {wav_path}")
        
        print(f"🎧 Распознаю речь (передаю путь к файлу)...")
        
        # ВАЖНО: Передаём ПУТЬ к файлу, а не numpy array!
        # НЕ указываем language - Whisper автоматически определит язык (русский или английский)
        result = model.transcribe(
            wav_path,
            task="transcribe",  # Только транскрипция (не перевод)
            fp16=False,
            verbose=True  # Показывать процесс распознавания
        )

        # Получаем текст
        text = result["text"].strip()

        # Определяем язык распознанного текста
        detected_language = result.get("language", "unknown")
        print(f"🌍 Detected language: {detected_language}")

        # Если определен странный язык (не ru, не en) - пробуем заново с language="en"
        if detected_language not in ["ru", "en", "russian", "english"]:
            print(f"⚠️ Странный язык '{detected_language}', пробую заново с language='en'...")
            result = model.transcribe(
                wav_path,
                language="en",
                task="transcribe",
                fp16=False,
                verbose=False
            )
            text = result["text"].strip()
            detected_language = "en"
            print(f"✅ Перераспознано с language='en': '{text}'")

        # Удаляем неанглийские символы (китайские, арабские и т.д.)
        # Но сохраняем кириллицу если язык русский
        if text:
            original_text = text
            if detected_language in ["ru", "russian"]:
                # Для русского удаляем только неалфавитные символы (китайские и т.д.)
                text = re.sub(r'[^\u0400-\u04FF\w\s\'\"\.,!?\-]', '', text)
            else:
                # Для английского удаляем всё кроме латиницы
                text = clean_non_english_chars(text)

            text = re.sub(r'\s+', ' ', text).strip()

            if original_text != text:
                print(f"⚠️ Удалены неалфавитные символы: '{original_text}' → '{text}'")
        
        # Показываем также segments (части речи)
        if "segments" in result and result["segments"]:
            print(f"📝 Segments найдено: {len(result['segments'])}")
            for i, seg in enumerate(result["segments"][:3]):  # Первые 3
                print(f"  Segment {i+1}: '{seg['text'].strip()}'")
        
        if text:
            print(f"✅ Распознано: '{text}'")
        else:
            print("⚠️ Whisper вернул пустую строку")
            print(f"⚠️ Проверь что голосовое НЕ пустое и достаточно громкое")
        
        # Удаляем временный WAV
        if wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except:
                pass
        
        return text if text else None
        
    except Exception as e:
        print(f"❌ Whisper error: {e}")
        import traceback
        traceback.print_exc()
        
        # Удаляем временный WAV
        if wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except:
                pass
        
        return None