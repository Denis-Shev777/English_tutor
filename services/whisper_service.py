from faster_whisper import WhisperModel
import os
from pydub import AudioSegment
import tempfile

print("🎧 Загрузка Faster-Whisper модели...")

# Используем модель "base" с CPU - быстрее и легче чем openai-whisper
model = WhisperModel("base", device="cpu", compute_type="int8")

print("✅ Faster-Whisper готов!")

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
        
        print(f"🎧 Распознаю речь через Faster-Whisper...")

        # Faster-Whisper API: transcribe возвращает (segments, info)
        segments, info = model.transcribe(
            wav_path,
            language="en",
            beam_size=5,
            vad_filter=True  # Фильтр голосовой активности
        )

        # Собираем текст из сегментов
        text_parts = []
        segment_count = 0
        for segment in segments:
            text_parts.append(segment.text.strip())
            segment_count += 1
            if segment_count <= 3:  # Показываем первые 3 сегмента
                print(f"  Segment {segment_count}: '{segment.text.strip()}'")

        text = " ".join(text_parts).strip()

        if text:
            print(f"✅ Распознано: '{text}'")
            print(f"📝 Всего сегментов: {segment_count}")
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