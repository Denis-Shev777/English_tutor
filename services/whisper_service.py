from faster_whisper import WhisperModel
import os
import re
from pydub import AudioSegment
import tempfile

print("🎧 Загрузка Faster-Whisper модели...")

# Для English распознавания "small.en" обычно точнее, чем "base".
# Можно переопределить через .env: WHISPER_MODEL=base/small.en/medium.en
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small.en")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)

print("✅ Faster-Whisper готов!")


# Подсказка словаря для разговоров в боте (улучшает распознавание редких слов).
BIAS_PROMPT = (
    "English tutoring dialogue. Common words and phrases: latte, cappuccino, espresso, "
    "americano, menu, order, coffee, tea, bill, to go, stay here, recommendation."
)


def _postprocess_stt_text(text: str) -> str:
    """Легкая нормализация типичных ошибок STT для coffee-сценариев."""
    if not text:
        return text

    cleaned = text.strip()
    lower = cleaned.lower()

    # Частый кейс: "lot of" вместо "latte" в контексте кофе/заказа.
    if ("coffee" in lower or "order" in lower or "cafe" in lower) and "lot of" in lower:
        cleaned = re.sub(r"\blot of\b", "latte", cleaned, flags=re.IGNORECASE)

    # Частый кейс: "coffee later" вместо "coffee latte".
    if ("coffee" in lower or "order" in lower or "cafe" in lower) and "later" in lower:
        cleaned = re.sub(r"\blater\b", "latte", cleaned, flags=re.IGNORECASE)

    return cleaned

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

        def _run_transcribe(beam_size: int, use_vad: bool, with_prompt: bool):
            kwargs = {
                "language": "en",
                "beam_size": beam_size,
                "vad_filter": use_vad,
                "temperature": 0.0,
                "condition_on_previous_text": False,
            }
            if with_prompt:
                kwargs["initial_prompt"] = BIAS_PROMPT
            segs, inf = model.transcribe(wav_path, **kwargs)
            parts = []
            count = 0
            for seg in segs:
                s = seg.text.strip()
                if s:
                    parts.append(s)
                    count += 1
                    if count <= 3:
                        print(f"  Segment {count}: '{s}'")
            return " ".join(parts).strip(), count, inf

        # 1) Основной проход.
        text, segment_count, info = _run_transcribe(beam_size=6, use_vad=True, with_prompt=True)

        # 2) Fallback: для коротких/сомнительных результатов делаем второй проход.
        needs_retry = (
            not text
            or len(text.split()) <= 2
            or " lot of " in f" {text.lower()} "
            or text.lower().endswith(" later")
        )
        if needs_retry:
            print("⚠️ Результат сомнительный, запускаю повторное распознавание...")
            retry_text, retry_count, _ = _run_transcribe(
                beam_size=10, use_vad=False, with_prompt=True
            )
            if retry_text and (len(retry_text) >= len(text)):
                text = retry_text
                segment_count = retry_count

        if text:
            text = _postprocess_stt_text(text)
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
