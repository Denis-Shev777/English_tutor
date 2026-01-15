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

RULES:
1. ALL strings must be in double quotes
2. quick_replies should have 2-4 short options (max 20 characters each)
3. For A1/A2 students: always provide simple quick_replies
4. For vocabulary questions, add Russian translation in tip field
5. Keep reply concise (2-3 sentences)
6. NO meta-commentary, NO parentheses explanations
7. Output ONLY valid JSON, nothing else"""

def check_word_and_suggest(user_text: str):
    """Проверяет слово и предлагает варианты если не найдено"""
    
    patterns = [
        r"what\s+(?:does|is)\s+(?:mean\s+)?(\w+)",
        r"what\s+is\s+mean\s+(\w+)",
        r"meaning\s+of\s+(\w+)",
        r"translate\s+(?:please\s+)?(\w+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, user_text.lower())
        if match:
            word = match.group(1).lower()
            
            if word not in COMMON_WORDS:
                suggestions = get_close_matches(word, COMMON_WORDS, n=3, cutoff=0.6)
                
                if suggestions:
                    return f"I do not know the word '{word}'. Did you mean: {', '.join(suggestions)}? Let me know which one!"
    
    return None

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

                # Fallback: возвращаем простой ответ
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