import requests
import json
import re
from datetime import datetime
from difflib import get_close_matches

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3:latest"

COMMON_WORDS = {
    # === БАЗОВЫЕ СЛОВА ===
    # Животные
    "cat", "dog", "bird", "fish", "horse", "cow", "pig", "chicken", "mouse", "pet",
    
    # Дом и места
    "house", "home", "flat", "apartment", "room", "kitchen", "bedroom", "bathroom",
    "door", "window", "wall", "floor", "roof", "garden", "yard", "building",
    "city", "town", "village", "country", "street", "road", "bridge", "shop", "store",
    
    # Транспорт
    "car", "bus", "train", "plane", "bike", "bicycle", "ship", "boat", "metro", "subway",
    "taxi", "truck", "motorcycle", "helicopter",
    
    # Природа
    "tree", "flower", "plant", "grass", "leaf", "river", "lake", "sea", "ocean",
    "mountain", "hill", "forest", "sky", "sun", "moon", "star", "cloud", "rain",
    "snow", "wind", "fire", "water", "earth", "stone", "rock", "beach", "island",
    
    # === ТУРИЗМ И ПУТЕШЕСТВИЯ ===
    "travel", "trip", "journey", "tour", "tourist", "vacation", "holiday", "resort",
    "hotel", "hostel", "motel", "inn", "accommodation", "reservation", "booking",
    "airport", "flight", "ticket", "boarding", "gate", "departure", "arrival",
    "passport", "visa", "customs", "luggage", "baggage", "suitcase", "backpack",
    "guide", "map", "destination", "route", "itinerary", "excursion", "sightseeing",
    "souvenir", "attraction", "landmark", "museum", "gallery", "monument",
    "cruise", "camping", "hiking", "adventure", "explorer",
    
    # === БИЗНЕС ===
    "business", "company", "corporation", "firm", "enterprise", "startup",
    "office", "manager", "director", "boss", "employee", "staff", "team", "colleague",
    "meeting", "conference", "presentation", "report", "project", "task", "deadline",
    "contract", "agreement", "deal", "partnership", "client", "customer", "supplier",
    "profit", "loss", "revenue", "income", "expense", "budget", "investment",
    "salary", "wage", "bonus", "commission", "payment", "invoice", "receipt",
    "marketing", "sales", "advertising", "promotion", "brand", "strategy",
    "negotiation", "proposal", "quotation", "tender", "outsourcing",
    
    # === ИНТЕРНЕТ И ТЕХНОЛОГИИ ===
    "internet", "online", "offline", "website", "webpage", "blog", "forum",
    "email", "message", "chat", "video", "call", "zoom", "skype",
    "app", "application", "software", "program", "system", "platform",
    "download", "upload", "install", "update", "upgrade", "delete",
    "computer", "laptop", "tablet", "phone", "smartphone", "mobile",
    "screen", "keyboard", "mouse", "printer", "scanner", "camera",
    "wifi", "bluetooth", "network", "connection", "server", "cloud",
    "password", "username", "account", "profile", "settings",
    "social", "media", "facebook", "instagram", "twitter", "youtube",
    "google", "search", "browser", "link", "url", "click",
    "data", "file", "folder", "document", "backup", "storage",
    "virus", "security", "firewall", "encryption", "privacy",
    "coding", "programming", "developer", "software", "hardware",
    "artificial", "intelligence", "robot", "automation", "digital",
    
    # === БЬЮТИ ИНДУСТРИЯ ===
    "beauty", "makeup", "cosmetics", "skincare", "haircare",
    "salon", "spa", "barbershop", "hairdresser", "stylist", "beautician",
    "haircut", "hairstyle", "hair", "coloring", "dyeing", "bleaching",
    "manicure", "pedicure", "nails", "polish", "gel",
    "facial", "massage", "treatment", "therapy", "procedure",
    "cream", "lotion", "serum", "mask", "cleanser", "toner",
    "lipstick", "mascara", "foundation", "powder", "blush", "eyeshadow",
    "perfume", "fragrance", "scent", "cologne",
    "skin", "face", "body", "hair", "nails", "lips", "eyes",
    "wrinkle", "acne", "scar", "blemish", "tan", "pale",
    
    # === МОДА ===
    "fashion", "style", "trend", "look", "outfit", "wardrobe",
    "clothes", "clothing", "dress", "shirt", "blouse", "skirt", "pants", "jeans",
    "jacket", "coat", "sweater", "hoodie", "shoes", "boots", "sneakers",
    "accessories", "bag", "belt", "hat", "scarf", "gloves", "jewelry",
    "brand", "designer", "boutique", "shopping", "sale", "discount",
    "size", "fit", "color", "pattern", "fabric", "material", "leather",
    
    # === ЗДОРОВЬЕ И МЕДИЦИНА ===
    "health", "medicine", "medical", "doctor", "nurse", "patient",
    "hospital", "clinic", "pharmacy", "drugstore",
    "disease", "illness", "sickness", "pain", "ache", "fever", "cold", "flu",
    "treatment", "therapy", "surgery", "operation", "examination", "checkup",
    "prescription", "pill", "tablet", "capsule", "injection", "vaccine",
    "healthy", "sick", "ill", "tired", "weak", "strong", "fit",
    "symptom", "diagnosis", "recovery", "cure", "healing",
    
    # === СПОРТ И ФИТНЕС ===
    "sport", "sports", "gym", "fitness", "workout", "exercise", "training",
    "coach", "trainer", "athlete", "player", "team", "match", "game", "competition",
    "running", "jogging", "swimming", "cycling", "yoga", "pilates",
    "football", "soccer", "basketball", "tennis", "golf", "boxing",
    "muscle", "strength", "cardio", "stretching", "warm-up", "cool-down",
    
    # === ЕДА И РЕСТОРАНЫ ===
    "food", "meal", "dish", "cuisine", "recipe", "ingredient", "cooking",
    "restaurant", "cafe", "bar", "pub", "canteen", "cafeteria",
    "menu", "order", "waiter", "waitress", "chef", "cook",
    "breakfast", "lunch", "dinner", "snack", "dessert", "appetizer",
    "meat", "chicken", "beef", "pork", "fish", "seafood",
    "vegetable", "fruit", "salad", "soup", "pasta", "pizza", "burger",
    "bread", "rice", "potato", "egg", "cheese", "milk", "butter",
    "coffee", "tea", "juice", "water", "wine", "beer", "cocktail",
    "delicious", "tasty", "yummy", "spicy", "sweet", "sour", "bitter", "salty",
    
    # === ФИНАНСЫ ===
    "money", "cash", "credit", "debit", "card", "account", "balance",
    "bank", "banking", "branch", "atm", "transfer", "deposit", "withdrawal",
    "loan", "mortgage", "interest", "rate", "debt", "payment", "installment",
    "currency", "dollar", "euro", "pound", "exchange", "forex",
    "investment", "investor", "stock", "share", "portfolio", "dividend",
    "insurance", "policy", "premium", "claim", "coverage",
    "tax", "fee", "charge", "cost", "price", "value", "worth",
    
    # === ОБРАЗОВАНИЕ ===
    "education", "school", "university", "college", "institute", "academy",
    "student", "pupil", "teacher", "professor", "lecturer", "tutor",
    "class", "lesson", "course", "subject", "program", "curriculum",
    "exam", "test", "quiz", "homework", "assignment", "project",
    "grade", "mark", "score", "diploma", "degree", "certificate",
    "study", "learn", "teach", "practice", "training", "knowledge",
    
    # === РАБОТА ===
    "work", "job", "career", "profession", "occupation", "position",
    "hire", "employ", "recruit", "interview", "resume", "cv",
    "experience", "skill", "qualification", "expertise", "ability",
    "full-time", "part-time", "freelance", "remote", "office",
    "shift", "schedule", "overtime", "leave", "vacation", "sick",
    
    # === ОБЩИЕ ГЛАГОЛЫ ===
    "be", "have", "do", "make", "get", "go", "come", "see", "look", "take",
    "give", "use", "find", "tell", "ask", "work", "call", "try", "need", "feel",
    "become", "leave", "put", "mean", "keep", "let", "begin", "seem", "help",
    "talk", "turn", "start", "show", "hear", "play", "run", "move", "like",
    "live", "believe", "hold", "bring", "happen", "write", "sit", "stand",
    "lose", "pay", "meet", "include", "continue", "set", "learn", "change",
    "want", "know", "think", "understand", "speak", "read", "listen",
    
    # === ОБЩИЕ ПРИЛАГАТЕЛЬНЫЕ ===
    "good", "bad", "big", "small", "great", "new", "old", "high", "low",
    "long", "short", "young", "early", "late", "important", "different",
    "easy", "hard", "fast", "slow", "happy", "sad", "angry", "tired",
    "hot", "cold", "warm", "cool", "wet", "dry", "clean", "dirty",
    "beautiful", "ugly", "pretty", "handsome", "nice", "wonderful",
    "interesting", "boring", "exciting", "amazing", "fantastic",
    "true", "false", "right", "wrong", "correct", "incorrect",
    "safe", "dangerous", "careful", "careless", "strong", "weak",
    
    # === ПОЛЕЗНЫЕ СЛОВА ===
    "achieve", "achievement", "neither", "curious", "provide", "environment",
    "nature", "cosy", "accomplish", "challenge", "success", "goal", "dream",
    "hope", "future", "present", "past", "reason", "idea", "question", "answer",
    "problem", "solution", "way", "method", "approach", "technique",
    "information", "knowledge", "fact", "truth", "lie", "secret",
    "time", "day", "week", "month", "year", "moment", "period",
    "place", "location", "area", "region", "zone", "space", "room",
    "people", "person", "human", "man", "woman", "child", "family",
    "world", "life", "death", "birth", "age", "generation"
}

SYSTEM_PROMPT = """You are a friendly and encouraging English teacher helping Russian speakers improve their conversational English.

CRITICAL: You MUST respond ONLY with valid JSON in this exact format:
{
  "reply": "your natural English response",
  "question": "optional follow-up question to continue conversation",
  "quick_replies": ["option 1", "option 2", "option 3"],
  "correction": "if user made grammar mistake, show corrected version here",
  "tip": "optional grammar tip in Russian"
}

EXAMPLE of valid JSON:
{"reply": "Hi there!", "question": "How are you?", "quick_replies": ["I'm fine", "Not bad", "Great"], "correction": "", "tip": ""}

LEVEL-SPECIFIC GUIDELINES:

**A1 (Beginner):**
- Use ONLY simple present/past tense
- Vocabulary: 500-1000 most common words (family, food, colors, numbers, basic verbs)
- Sentences: 5-8 words maximum
- Questions: Yes/No questions or simple What/Where/When
- Examples: "I like cats", "Where are you from?", "What is your name?"
- ALWAYS provide 3-4 simple quick_replies
- Correct gently, focus on basics

**A2 (Elementary):**
- Use present, past, future simple + present continuous
- Vocabulary: 1000-2000 words (daily activities, hobbies, shopping, travel basics)
- Sentences: 8-12 words
- Questions: Can include "Why" and "How" but keep simple
- Examples: "I am learning English", "What do you like to do on weekends?"
- Provide 2-3 quick_replies
- Introduce basic phrasal verbs carefully

**B1 (Intermediate):**
- Use past continuous, present perfect, modals (can, should, must)
- Vocabulary: 2000-3500 words (work, opinions, experiences, abstract concepts)
- Sentences: 12-18 words, can use compound sentences
- Questions: More complex, asking for opinions and experiences
- Examples: "Have you ever been to London?", "What would you do if...?"
- IMPORTANT: NO quick_replies - student can form own responses
- Explain idioms and expressions

**B2 (Upper-Intermediate):**
- Use all tenses including conditionals, passive voice
- Vocabulary: 3500+ words (professional, academic, nuanced expressions)
- Sentences: No limit, use complex structures
- Questions: Abstract, hypothetical, analytical
- Examples: "If you had known about this earlier, would you have acted differently?"
- CRITICAL: NEVER provide quick_replies - advanced students don't need them
- Discuss complex topics, introduce advanced grammar

ADAPTATION RULES:
1. Lower levels = shorter sentences, simpler words, more support
2. Higher levels = complex grammar, rich vocabulary, abstract topics
3. ALL levels: be encouraging, patient, natural
4. Match your complexity to student's level STRICTLY

GENERAL RULES:
1. ALL strings must be in double quotes
2. quick_replies should have 2-4 short options (max 20 characters each)
3. For vocabulary questions, add Russian translation in tip field
4. Keep reply concise (2-3 sentences for A1-A2, 3-4 for B1-B2)
5. NO meta-commentary, NO parentheses explanations
6. Output ONLY valid JSON, nothing else"""

def is_russian_query(user_text: str):
    """
    Проверяет, является ли сообщение запросом на русском языке
    Returns: (bool, str, str) - (True/False, query_type, extracted_text)
    query_type: 'translate_to_en', 'translate_to_ru', 'what_means'
    """
    # "Переведи: слово" или "Переведи слово"
    match = re.search(r'переведи[\s:]+(.+)', user_text, re.IGNORECASE)
    if match:
        return (True, 'translate_to_en', match.group(1).strip())

    # "Что значит слово" или "Что означает слово"
    match = re.search(r'что\s+(?:значит|означает)[\s:]+(.+)', user_text, re.IGNORECASE)
    if match:
        return (True, 'what_means', match.group(1).strip())

    # "Как будет на английском: слово" или "Как сказать ... на английском"
    match = re.search(r'как\s+(?:будет|сказать)(?:\s+на\s+английском)?[\s:]+(.+?)(?:\s+на\s+английском)?$', user_text, re.IGNORECASE)
    if match:
        return (True, 'translate_to_en', match.group(1).strip())

    # "Как по-английски: слово"
    match = re.search(r'как\s+по-английски[\s:]+(.+)', user_text, re.IGNORECASE)
    if match:
        return (True, 'translate_to_en', match.group(1).strip())

    return (False, None, None)

def is_translation_request(user_text: str):
    """
    Проверяет, является ли сообщение запросом на перевод/объяснение слова
    Returns: (bool, str) - (True/False, extracted_word или None)
    """
    patterns = [
        # "Word: [word]" или "Word [word]" - ПРИОРИТЕТ!
        r"word[\s:]+['\"]?(\w+)['\"]?",
        # "Translate, [word]" или "Translate [word]"
        r"translate[\s,]+['\"]?(\w+)['\"]?",
        # "What is/does [word] mean" (НЕ "what is it [word]")
        r"what\s+(?:does|is)\s+['\"]?(\w+)['\"]?\s+mean",
        # "What mean [word]" / "What's mean [word]"
        r"what'?s?\s+mean\s+['\"]?(\w+)['\"]?",
        # "Meaning of [word]"
        r"meaning\s+of\s+['\"]?(\w+)['\"]?",
        # "Give me situation/example with word..."
        r"give\s+me\s+(?:a\s+)?(?:situation|example|sentence)\s+(?:with\s+)?(?:word\s+)?['\"]?(\w+)['\"]?",
        r"situation\s+with\s+(?:word\s+)?['\"]?(\w+)['\"]?",
        r"example\s+with\s+(?:word\s+)?['\"]?(\w+)['\"]?",
        # "Use word ... in sentence"
        r"use\s+(?:word\s+)?['\"]?(\w+)['\"]?\s+in\s+(?:a\s+)?(?:sentence|example)",
        r"how\s+to\s+use\s+['\"]?(\w+)['\"]?",
        # "Explain [word]"
        r"explain\s+(?:word\s+)?['\"]?(\w+)['\"]?",
    ]

    for pattern in patterns:
        match = re.search(pattern, user_text.lower())
        if match:
            word = match.group(1).lower()
            # Игнорируем служебные слова
            if word in ['it', 'is', 'a', 'an', 'the', 'for', 'to', 'of', 'in', 'on', 'at', 'me', 'you', 'please']:
                continue
            return (True, word)

    return (False, None)

def get_russian_translation(russian_text: str, user_level: str = None):
    """
    Перевод с русского на английский с объяснением
    """
    level_note = f"\nStudent level: {user_level}" if user_level else ""

    prompt = f"""You are an English teacher. A Russian-speaking student asked: "How to say '{russian_text}' in English?"

Provide a SIMPLE, DIRECT response in this EXACT JSON format:
{{
  "reply": "In English, we say: [ONE SIMPLE TRANSLATION ONLY] (Russian: {russian_text})",
  "question": "Example: [ONE SIMPLE SENTENCE] (Пример: [простой русский перевод])",
  "quick_replies": [],
  "correction": "",
  "tip": ""
}}

CRITICAL RULES:
1. Give ONLY ONE simple, direct translation - the most common word
2. NO explanations, NO history, NO additional info - just the translation!
3. Example: If "{russian_text}" = "ручка", reply MUST be: "In English, we say: pen (Russian: ручка)"
4. Example sentence must be VERY SIMPLE, like "I have a pen" or "This is a pen"
5. For A1-A2 levels: use only basic words and simple present tense
6. Russian text MUST be in parentheses so TTS can skip it{level_note}
7. Keep it SHORT and SIMPLE - beginners need clarity, not complexity!

BAD example (TOO COMPLEX):
"The English pen is actually called a 'fountain pen' or simply a 'pen'. It's used for writing..."

GOOD example (SIMPLE):
"In English, we say: pen (Russian: ручка)"

Respond ONLY with valid JSON:"""

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "max_tokens": 250
                }
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            raw_response = result.get("response", "").strip()

            try:
                json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    parsed = json.loads(json_str)
                    return {
                        "reply": parsed.get("reply", ""),
                        "question": parsed.get("question", ""),
                        "quick_replies": parsed.get("quick_replies", []),
                        "correction": parsed.get("correction", ""),
                        "tip": parsed.get("tip", "")
                    }
            except (json.JSONDecodeError, ValueError) as e:
                print(f"JSON parse error in Russian translation: {e}")

        # Fallback
        return {
            "reply": f"In English, we say: [translation] (Russian: {russian_text})",
            "question": f"Let me give you an example (Давай пример)",
            "quick_replies": [],
            "correction": "",
            "tip": ""
        }

    except Exception as e:
        print(f"Error getting Russian translation: {e}")
        return {
            "reply": f"Let me help you translate '{russian_text}' to English (Помогу тебе перевести '{russian_text}' на английский)",
            "question": "",
            "quick_replies": [],
            "correction": "",
            "tip": ""
        }

def get_word_explanation(word: str, user_level: str = None):
    """
    Получить объяснение слова с переводом и примером
    """
    level_note = f"\nStudent level: {user_level}" if user_level else ""

    prompt = f"""You are an English teacher. A student asked about the word "{word}".

Provide a response in this EXACT JSON format:
{{
  "reply": "The word '{word}' means [explanation in simple English] (Russian: [перевод])",
  "question": "Example: [sentence with '{word}'] (Пример: [русский перевод предложения])",
  "quick_replies": [],
  "correction": "",
  "tip": ""
}}

CRITICAL REQUIREMENTS:
1. In "reply": give clear English explanation, then add Russian translation IN PARENTHESES: (Russian: перевод)
2. In "question": provide ONE example sentence, then add full Russian translation IN PARENTHESES: (Пример: перевод)
3. Example format for "reply": "The word 'breed' means a type or kind of animal (Russian: порода)"
4. Example format for "question": "Example: The dog is a friendly breed (Пример: Собака — дружелюбная порода)"
5. IMPORTANT: Russian text MUST be in parentheses so TTS can skip it{level_note}
6. Output ONLY valid JSON, nothing else

Respond ONLY with valid JSON:"""

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "max_tokens": 250
                }
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            raw_response = result.get("response", "").strip()

            # Парсим JSON
            try:
                json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    parsed = json.loads(json_str)
                    return {
                        "reply": parsed.get("reply", ""),
                        "question": parsed.get("question", ""),
                        "quick_replies": parsed.get("quick_replies", []),
                        "correction": parsed.get("correction", ""),
                        "tip": parsed.get("tip", "")
                    }
            except (json.JSONDecodeError, ValueError) as e:
                print(f"JSON parse error in word explanation: {e}")

        # Fallback
        return {
            "reply": f"The word '{word}' is an English word (Слово '{word}' - английское слово)",
            "question": f"Example: I use the word '{word}' often (Пример: Я часто использую слово '{word}')",
            "quick_replies": [],
            "correction": "",
            "tip": ""
        }

    except Exception as e:
        print(f"Error getting word explanation: {e}")
        return {
            "reply": f"I can help you with the word '{word}' (Я помогу тебе со словом '{word}')",
            "question": "",
            "quick_replies": [],
            "correction": "",
            "tip": ""
        }

def get_ollama_response(user_text: str, history: list = None, user_level: str = None):
    """
    Получить ответ от LLaMA в JSON формате

    Returns:
        dict: {
            "reply": str,
            "question": str,
            "quick_replies": list,
            "correction": str,
            "tip": str
        }
    """

    # Формируем историю разговора
    conversation = ""
    if history:
        for role, content in history[-8:]:
            if role == "user":
                conversation += f"\nStudent: {content}"
            else:
                # Если в истории JSON, извлекаем только reply
                if isinstance(content, str) and content.startswith("{"):
                    try:
                        parsed = json.loads(content)
                        conversation += f"\nTeacher: {parsed.get('reply', content)}"
                    except:
                        conversation += f"\nTeacher: {content}"
                else:
                    conversation += f"\nTeacher: {content}"

    current_date = datetime.now().strftime("%A, %B %d, %Y")
    level_note = f"\nStudent level: {user_level}" if user_level else ""

    full_prompt = f"""{SYSTEM_PROMPT}

IMPORTANT: Today's date is {current_date}.{level_note}

Conversation history:{conversation}

Student: {user_text}
Teacher (respond ONLY with valid JSON):"""

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": MODEL_NAME,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.5,
                    "top_p": 0.9,
                    "max_tokens": 300
                }
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            raw_response = result.get("response", "").strip()

            # Пытаемся распарсить JSON
            try:
                # Убираем возможный мусор до/после JSON
                json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    parsed = json.loads(json_str)

                    # Проверяем обязательные поля
                    return {
                        "reply": parsed.get("reply", ""),
                        "question": parsed.get("question", ""),
                        "quick_replies": parsed.get("quick_replies", []),
                        "correction": parsed.get("correction", ""),
                        "tip": parsed.get("tip", "")
                    }
                else:
                    raise ValueError("No JSON found in response")

            except (json.JSONDecodeError, ValueError) as e:
                print(f"JSON parse error: {e}")
                print(f"Raw response: {raw_response}")

                # FALLBACK: Парсим через регулярки
                try:
                    reply_match = re.search(r'"reply"\s*:\s*"?([^"]*?)"?\s*[,\n}]', raw_response, re.DOTALL)
                    question_match = re.search(r'"question"\s*:\s*"?([^"]*?)"?\s*[,\n}]', raw_response, re.DOTALL)
                    correction_match = re.search(r'"correction"\s*:\s*"?([^"]*?)"?\s*[,\n}]', raw_response, re.DOTALL)
                    tip_match = re.search(r'"tip"\s*:\s*"?([^"]*?)"?\s*[,\n}]', raw_response, re.DOTALL)

                    # Парсим quick_replies как массив
                    quick_replies = []
                    qr_match = re.search(r'"quick_replies"\s*:\s*\[(.*?)\]', raw_response, re.DOTALL)
                    if qr_match:
                        qr_str = qr_match.group(1)
                        # Извлекаем все строки в кавычках
                        quick_replies = re.findall(r'"([^"]+)"', qr_str)

                    fallback_result = {
                        "reply": reply_match.group(1).strip() if reply_match else raw_response[:200],
                        "question": question_match.group(1).strip() if question_match else "",
                        "quick_replies": quick_replies,
                        "correction": correction_match.group(1).strip() if correction_match else "",
                        "tip": tip_match.group(1).strip() if tip_match else ""
                    }

                    print(f"✅ Fallback parsing успешен: {fallback_result}")
                    return fallback_result

                except Exception as fallback_error:
                    print(f"Fallback parsing failed: {fallback_error}")
                    # Последний fallback - возвращаем простой ответ
                    return {
                        "reply": raw_response if raw_response else "Sorry, I couldn't understand that.",
                        "question": "",
                        "quick_replies": [],
                        "correction": "",
                        "tip": ""
                    }
        else:
            print(f"Ollama API error: {response.status_code}")
            return {
                "reply": "Sorry, I'm having trouble connecting right now. Please try again!",
                "question": "",
                "quick_replies": [],
                "correction": "",
                "tip": ""
            }

    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return {
            "reply": "Sorry, something went wrong. Please try again!",
            "question": "",
            "quick_replies": [],
            "correction": "",
            "tip": ""
        }