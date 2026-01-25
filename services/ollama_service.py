import requests
import re
import json
import os
from datetime import datetime
from difflib import get_close_matches
from logger import get_logger
from groq import Groq

logger = get_logger(__name__)

# Groq client initialization (FREE!)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL_NAME = "llama-3.1-8b-instant"  # Быстрая бесплатная модель

COMMON_WORDS = {
    # === БАЗОВЫЕ СЛОВА ===
    # Животные
    "cat",
    "dog",
    "bird",
    "fish",
    "horse",
    "cow",
    "pig",
    "chicken",
    "mouse",
    "pet",
    # Дом и места
    "house",
    "home",
    "flat",
    "apartment",
    "room",
    "kitchen",
    "bedroom",
    "bathroom",
    "door",
    "window",
    "wall",
    "floor",
    "roof",
    "garden",
    "yard",
    "building",
    "city",
    "town",
    "village",
    "country",
    "street",
    "road",
    "bridge",
    "shop",
    "store",
    # Транспорт
    "car",
    "bus",
    "train",
    "plane",
    "bike",
    "bicycle",
    "ship",
    "boat",
    "metro",
    "subway",
    "taxi",
    "truck",
    "motorcycle",
    "helicopter",
    # Природа
    "tree",
    "flower",
    "plant",
    "grass",
    "leaf",
    "river",
    "lake",
    "sea",
    "ocean",
    "mountain",
    "hill",
    "forest",
    "sky",
    "sun",
    "moon",
    "star",
    "cloud",
    "rain",
    "snow",
    "wind",
    "fire",
    "water",
    "earth",
    "stone",
    "rock",
    "beach",
    "island",
    # === ТУРИЗМ И ПУТЕШЕСТВИЯ ===
    "travel",
    "trip",
    "journey",
    "tour",
    "tourist",
    "vacation",
    "holiday",
    "resort",
    "hotel",
    "hostel",
    "motel",
    "inn",
    "accommodation",
    "reservation",
    "booking",
    "airport",
    "flight",
    "ticket",
    "boarding",
    "gate",
    "departure",
    "arrival",
    "passport",
    "visa",
    "customs",
    "luggage",
    "baggage",
    "suitcase",
    "backpack",
    "guide",
    "map",
    "destination",
    "route",
    "itinerary",
    "excursion",
    "sightseeing",
    "souvenir",
    "attraction",
    "landmark",
    "museum",
    "gallery",
    "monument",
    "cruise",
    "camping",
    "hiking",
    "adventure",
    "explorer",
    # === БИЗНЕС ===
    "business",
    "company",
    "corporation",
    "firm",
    "enterprise",
    "startup",
    "office",
    "manager",
    "director",
    "boss",
    "employee",
    "staff",
    "team",
    "colleague",
    "meeting",
    "conference",
    "presentation",
    "report",
    "project",
    "task",
    "deadline",
    "contract",
    "agreement",
    "deal",
    "partnership",
    "client",
    "customer",
    "supplier",
    "profit",
    "loss",
    "revenue",
    "income",
    "expense",
    "budget",
    "investment",
    "salary",
    "wage",
    "bonus",
    "commission",
    "payment",
    "invoice",
    "receipt",
    "marketing",
    "sales",
    "advertising",
    "promotion",
    "brand",
    "strategy",
    "negotiation",
    "proposal",
    "quotation",
    "tender",
    "outsourcing",
    # === ИНТЕРНЕТ И ТЕХНОЛОГИИ ===
    "internet",
    "online",
    "offline",
    "website",
    "webpage",
    "blog",
    "forum",
    "email",
    "message",
    "chat",
    "video",
    "call",
    "zoom",
    "skype",
    "app",
    "application",
    "software",
    "program",
    "system",
    "platform",
    "download",
    "upload",
    "install",
    "update",
    "upgrade",
    "delete",
    "computer",
    "laptop",
    "tablet",
    "phone",
    "smartphone",
    "mobile",
    "screen",
    "keyboard",
    "mouse",
    "printer",
    "scanner",
    "camera",
    "wifi",
    "bluetooth",
    "network",
    "connection",
    "server",
    "cloud",
    "password",
    "username",
    "account",
    "profile",
    "settings",
    "social",
    "media",
    "facebook",
    "instagram",
    "twitter",
    "youtube",
    "google",
    "search",
    "browser",
    "link",
    "url",
    "click",
    "data",
    "file",
    "folder",
    "document",
    "backup",
    "storage",
    "virus",
    "security",
    "firewall",
    "encryption",
    "privacy",
    "coding",
    "programming",
    "developer",
    "software",
    "hardware",
    "artificial",
    "intelligence",
    "robot",
    "automation",
    "digital",
    # === БЬЮТИ ИНДУСТРИЯ ===
    "beauty",
    "makeup",
    "cosmetics",
    "skincare",
    "haircare",
    "salon",
    "spa",
    "barbershop",
    "hairdresser",
    "stylist",
    "beautician",
    "haircut",
    "hairstyle",
    "hair",
    "coloring",
    "dyeing",
    "bleaching",
    "manicure",
    "pedicure",
    "nails",
    "polish",
    "gel",
    "facial",
    "massage",
    "treatment",
    "therapy",
    "procedure",
    "cream",
    "lotion",
    "serum",
    "mask",
    "cleanser",
    "toner",
    "lipstick",
    "mascara",
    "foundation",
    "powder",
    "blush",
    "eyeshadow",
    "perfume",
    "fragrance",
    "scent",
    "cologne",
    "skin",
    "face",
    "body",
    "hair",
    "nails",
    "lips",
    "eyes",
    "wrinkle",
    "acne",
    "scar",
    "blemish",
    "tan",
    "pale",
    # === МОДА ===
    "fashion",
    "style",
    "trend",
    "look",
    "outfit",
    "wardrobe",
    "clothes",
    "clothing",
    "dress",
    "shirt",
    "blouse",
    "skirt",
    "pants",
    "jeans",
    "jacket",
    "coat",
    "sweater",
    "hoodie",
    "shoes",
    "boots",
    "sneakers",
    "accessories",
    "bag",
    "belt",
    "hat",
    "scarf",
    "gloves",
    "jewelry",
    "brand",
    "designer",
    "boutique",
    "shopping",
    "sale",
    "discount",
    "size",
    "fit",
    "color",
    "pattern",
    "fabric",
    "material",
    "leather",
    # === ЗДОРОВЬЕ И МЕДИЦИНА ===
    "health",
    "medicine",
    "medical",
    "doctor",
    "nurse",
    "patient",
    "hospital",
    "clinic",
    "pharmacy",
    "drugstore",
    "disease",
    "illness",
    "sickness",
    "pain",
    "ache",
    "fever",
    "cold",
    "flu",
    "treatment",
    "therapy",
    "surgery",
    "operation",
    "examination",
    "checkup",
    "prescription",
    "pill",
    "tablet",
    "capsule",
    "injection",
    "vaccine",
    "healthy",
    "sick",
    "ill",
    "tired",
    "weak",
    "strong",
    "fit",
    "symptom",
    "diagnosis",
    "recovery",
    "cure",
    "healing",
    # === СПОРТ И ФИТНЕС ===
    "sport",
    "sports",
    "gym",
    "fitness",
    "workout",
    "exercise",
    "training",
    "coach",
    "trainer",
    "athlete",
    "player",
    "team",
    "match",
    "game",
    "competition",
    "running",
    "jogging",
    "swimming",
    "cycling",
    "yoga",
    "pilates",
    "football",
    "soccer",
    "basketball",
    "tennis",
    "golf",
    "boxing",
    "muscle",
    "strength",
    "cardio",
    "stretching",
    "warm-up",
    "cool-down",
    # === ЕДА И РЕСТОРАНЫ ===
    "food",
    "meal",
    "dish",
    "cuisine",
    "recipe",
    "ingredient",
    "cooking",
    "restaurant",
    "cafe",
    "bar",
    "pub",
    "canteen",
    "cafeteria",
    "menu",
    "order",
    "waiter",
    "waitress",
    "chef",
    "cook",
    "breakfast",
    "lunch",
    "dinner",
    "snack",
    "dessert",
    "appetizer",
    "meat",
    "chicken",
    "beef",
    "pork",
    "fish",
    "seafood",
    "vegetable",
    "fruit",
    "salad",
    "soup",
    "pasta",
    "pizza",
    "burger",
    "bread",
    "rice",
    "potato",
    "egg",
    "cheese",
    "milk",
    "butter",
    "coffee",
    "tea",
    "juice",
    "water",
    "wine",
    "beer",
    "cocktail",
    "delicious",
    "tasty",
    "yummy",
    "spicy",
    "sweet",
    "sour",
    "bitter",
    "salty",
    # === ФИНАНСЫ ===
    "money",
    "cash",
    "credit",
    "debit",
    "card",
    "account",
    "balance",
    "bank",
    "banking",
    "branch",
    "atm",
    "transfer",
    "deposit",
    "withdrawal",
    "loan",
    "mortgage",
    "interest",
    "rate",
    "debt",
    "payment",
    "installment",
    "currency",
    "dollar",
    "euro",
    "pound",
    "exchange",
    "forex",
    "investment",
    "investor",
    "stock",
    "share",
    "portfolio",
    "dividend",
    "insurance",
    "policy",
    "premium",
    "claim",
    "coverage",
    "tax",
    "fee",
    "charge",
    "cost",
    "price",
    "value",
    "worth",
    # === ОБРАЗОВАНИЕ ===
    "education",
    "school",
    "university",
    "college",
    "institute",
    "academy",
    "student",
    "pupil",
    "teacher",
    "professor",
    "lecturer",
    "tutor",
    "class",
    "lesson",
    "course",
    "subject",
    "program",
    "curriculum",
    "exam",
    "test",
    "quiz",
    "homework",
    "assignment",
    "project",
    "grade",
    "mark",
    "score",
    "diploma",
    "degree",
    "certificate",
    "study",
    "learn",
    "teach",
    "practice",
    "training",
    "knowledge",
    # === РАБОТА ===
    "work",
    "job",
    "career",
    "profession",
    "occupation",
    "position",
    "hire",
    "employ",
    "recruit",
    "interview",
    "resume",
    "cv",
    "experience",
    "skill",
    "qualification",
    "expertise",
    "ability",
    "full-time",
    "part-time",
    "freelance",
    "remote",
    "office",
    "shift",
    "schedule",
    "overtime",
    "leave",
    "vacation",
    "sick",
    # === ОБЩИЕ ГЛАГОЛЫ ===
    "be",
    "have",
    "do",
    "make",
    "get",
    "go",
    "come",
    "see",
    "look",
    "take",
    "give",
    "use",
    "find",
    "tell",
    "ask",
    "work",
    "call",
    "try",
    "need",
    "feel",
    "become",
    "leave",
    "put",
    "mean",
    "keep",
    "let",
    "begin",
    "seem",
    "help",
    "talk",
    "turn",
    "start",
    "show",
    "hear",
    "play",
    "run",
    "move",
    "like",
    "live",
    "believe",
    "hold",
    "bring",
    "happen",
    "write",
    "sit",
    "stand",
    "lose",
    "pay",
    "meet",
    "include",
    "continue",
    "set",
    "learn",
    "change",
    "want",
    "know",
    "think",
    "understand",
    "speak",
    "read",
    "listen",
    # === ОБЩИЕ ПРИЛАГАТЕЛЬНЫЕ ===
    "good",
    "bad",
    "big",
    "small",
    "great",
    "new",
    "old",
    "high",
    "low",
    "long",
    "short",
    "young",
    "early",
    "late",
    "important",
    "different",
    "easy",
    "hard",
    "fast",
    "slow",
    "happy",
    "sad",
    "angry",
    "tired",
    "hot",
    "cold",
    "warm",
    "cool",
    "wet",
    "dry",
    "clean",
    "dirty",
    "beautiful",
    "ugly",
    "pretty",
    "handsome",
    "nice",
    "wonderful",
    "interesting",
    "boring",
    "exciting",
    "amazing",
    "fantastic",
    "true",
    "false",
    "right",
    "wrong",
    "correct",
    "incorrect",
    "safe",
    "dangerous",
    "careful",
    "careless",
    "strong",
    "weak",
    # === ПОЛЕЗНЫЕ СЛОВА ===
    "achieve",
    "achievement",
    "neither",
    "curious",
    "provide",
    "environment",
    "nature",
    "cosy",
    "accomplish",
    "challenge",
    "success",
    "goal",
    "dream",
    "hope",
    "future",
    "present",
    "past",
    "reason",
    "idea",
    "question",
    "answer",
    "problem",
    "solution",
    "way",
    "method",
    "approach",
    "technique",
    "information",
    "knowledge",
    "fact",
    "truth",
    "lie",
    "secret",
    "time",
    "day",
    "week",
    "month",
    "year",
    "moment",
    "period",
    "place",
    "location",
    "area",
    "region",
    "zone",
    "space",
    "room",
    "people",
    "person",
    "human",
    "man",
    "woman",
    "child",
    "family",
    "world",
    "life",
    "death",
    "birth",
    "age",
    "generation",
}

SYSTEM_PROMPT = """You are an English tutor for A1–B2 Russian-speaking students.
Respond ONLY in valid JSON format with the following keys:
- "reply": a friendly natural response to the student (required)
- "question": a follow-up question if appropriate (optional, omit if none)
- "quick_replies": array of 3 short English replies (max 6 words each) for A1/A2 levels (optional)
- "correction": corrected version of student's sentence if it had errors (MANDATORY if there are ANY mistakes!)
- "tip": very short grammar/vocab tip (optional)

CRITICAL RULES FOR ERROR CORRECTION:
- You MUST check EVERY student message for grammar, vocabulary, and spelling errors
- If you find ANY error (even small), you MUST provide "correction" field with the fixed sentence
- Common errors to catch: subject-verb agreement (I has → I have), articles (a/an/the), word order, tense errors
- Examples of what to correct:
  * "I has plan" → correction: "I have a plan"
  * "She go to school" → correction: "She goes to school"
  * "I am live in Moscow" → correction: "I live in Moscow"
- If sentence is 100% correct, omit "correction" field

RULES:
- ALWAYS wrap ALL string values in double quotes (").
- NEVER output labels like "Correct:", "Tip:", or "Question:".
- NEVER explain your JSON structure.
- Use only English in all fields except inside translation blocks (see below).

WORD MEANING FORMAT (when student asks "what is X" or "что значит X"):
For A1-A2 levels: Give VERY SIMPLE explanation (5-7 words max)
For B1-B2 levels: Can give more detailed explanation
ALWAYS include in "reply":
---
Animal - животное
Пример: I have a pet. It's an animal. - У меня есть питомец. Это животное.
---

- Keep "reply" conversational and human-like.
- For A1/A2, make "quick_replies" extremely simple.
- Output ONLY the JSON object. No extra text, no markdown, no ```json.
"""


def check_word_and_suggest(user_text: str):
    """Подсказки ТОЛЬКО если пользователь явно спрашивает значение ОДНОГО слова"""
    patterns = [
        r"^\s*what\s+does\s+(\w+)\s+mean\s*\??\s*$",
        r"^\s*what\s+is\s+(\w+)\s*\??\s*$",
        r"^\s*meaning\s+of\s+(\w+)\s*\??\s*$",
        r"^\s*translate\s+(\w+)\s*\??\s*$",
    ]

    for pattern in patterns:
        match = re.search(pattern, user_text.lower())
        if match:
            word = match.group(1).lower()

            # базовые слова НЕ трогаем вообще
            STOP_WORDS = {
                "your",
                "it",
                "please",
                "i",
                "you",
                "we",
                "they",
                "he",
                "she",
                "a",
                "an",
                "the",
                "to",
                "of",
                "in",
                "on",
            }
            if word in STOP_WORDS:
                return None

            if word not in COMMON_WORDS:
                suggestions = get_close_matches(word, COMMON_WORDS, n=3, cutoff=0.6)
                if suggestions:
                    return (
                        f"I’m not sure about '{word}'. Did you mean: {', '.join(suggestions)}?\n"
                        f"Reply with the correct one."
                    )

    return None


def call_ollama_raw(prompt: str) -> str:
    """Вызов Groq API (бесплатный Llama 3.1) - формат как в оригинальном Ollama"""
    try:
        # Отправляем весь промпт единым блоком как в оригинальной версии с Ollama
        # Это обеспечивает идентичное поведение модели
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            top_p=0.9,
            max_tokens=350,
        )

        bot_response = response.choices[0].message.content.strip()

        # чистим мусор
        bot_response = re.sub(r"\(Note:.*?\)", "", bot_response, flags=re.DOTALL)
        bot_response = re.sub(
            r"\(I corrected.*?\)", "", bot_response, flags=re.DOTALL
        )
        bot_response = bot_response.strip()

        # если вдруг модель вернула пустые поля перевода — убираем блок
        if "Perevod: None" in bot_response or "Primer: None" in bot_response:
            if "---" in bot_response:
                bot_response = bot_response.split("---")[0].strip()

        return bot_response

    except Exception as e:
        logger.error(f"Error calling Groq API: {e}", exc_info=True)
        return (
            "⚠️ Извините, сейчас технические неполадки с ИИ.\n"
            "Попробуйте отправить сообщение через минуту."
        )


def extract_word_from_query(user_text: str):
    """Извлекает слово из запроса о значении (на русском или английском)"""
    lower = user_text.strip().lower()

    # Паттерны для английских запросов
    en_patterns = [
        r"^\s*what\s+is\s+(?:mean\s+)?(\w+)\s*\??\s*$",         # what is mean animal / what is animal
        r"^\s*what\s+does\s+(\w+)\s+mean\s*\??\s*$",            # what does animal mean
        r"^\s*meaning\s+of\s+(\w+)\s*\??\s*$",                  # meaning of animal
        r"^\s*translate\s+(?:please\s+)?(\w+)\s*\??\s*$",       # translate animal / translate please animal
        r"^\s*what\s+is\s+mean\s+by\s+(\w+)\s*\??\s*$",         # what is mean by animal
        r"^\s*what's\s+(\w+)\s*\??\s*$",                        # what's animal
    ]

    # Паттерны для русских запросов
    ru_patterns = [
        r"^\s*(?:а\s+)?что\s+значит\s+(?:-\s*)?(\w+)\s*\??\s*$",         # что значит animal / а что значит animal
        r"^\s*(?:а\s+)?что\s+такое\s+(\w+)\s*\??\s*$",                   # что такое animal / а что такое dog
        r"^\s*значение\s+(\w+)\s*\??\s*$",                               # значение animal
        r"^\s*переведи\s+(?:слово\s+)?(?:пожалуйста\s+)?(\w+)\s*\??\s*$",  # переведи animal / переведи пожалуйста animal
        r"^\s*перевод\s+(\w+)\s*\??\s*$",                                # перевод animal
        r"^\s*(?:а\s+)?как\s+переводится\s+(\w+)\s*\??\s*$",             # как переводится animal / а как переводится dog
        r"^\s*(?:а\s+)?как\s+будет\s+(\w+)\s*\??\s*$",                   # как будет animal / а как будет dog
        r"^\s*(?:а\s+)?как\s+(?:по-английски|по\s+английски)\s+(\w+)\s*\??\s*$",  # а как по-английски собака
        r"^\s*(\w+)\s*-\s*это\s+что\s*\??\s*$",                          # animal - это что?
        r"^\s*(\w+)\s*-\s*что\s+это\s*\??\s*$",                          # animal - что это?
        r"^\s*что\s+означает\s+(\w+)\s*\??\s*$",                         # что означает animal
    ]

    for pattern in en_patterns + ru_patterns:
        match = re.search(pattern, lower)
        if match:
            return match.group(1)

    return None


def get_ollama_response(user_text: str, history: list = None, level: str = "A1"):
    """Получить структурированный ответ от Ollama в виде dict"""
    lower = user_text.strip().lower()

    # --- WORD MEANING MODE (приоритет!) ---
    word_to_explain = extract_word_from_query(user_text)
    if word_to_explain:
        # Специальный промпт для объяснения значения слова
        if level in ["A1", "A2"]:
            explain_prompt = f"""You are teaching English to A1-A2 beginner students.
Explain the word "{word_to_explain}" in VERY SIMPLE English.

Rules:
1. First line: ONE SHORT sentence (5-8 words) explaining the meaning
2. Second line: Word - Russian translation (ONLY ONE main translation)
3. Third line: Пример with translation

Example format:
Not the same.
Different - другой, различный
Пример: This pen is different. - Эта ручка другая.

Now explain "{word_to_explain}"."""
        else:
            explain_prompt = f"""You are teaching English to {level} students.
Explain the word "{word_to_explain}".

Rules:
1. First line: Clear short explanation
2. Second line: Word - Russian translation
3. Third line: Пример with translation

Example format:
Not the same as something else.
Different - другой, различный, отличающийся
Пример: Everyone is different in their own way. - Каждый по-своему уникален.

Now explain "{word_to_explain}"."""

        raw_explanation = call_ollama_raw(explain_prompt)
        return {
            "reply": raw_explanation,
            "question": None,
            "quick_replies": [],
            "correction": None,
            "tip": None,
        }

    # --- TRANSLATE MODE (полный текст) ---
    if (
        lower.startswith("translate")
        or lower.startswith("переведи")
        or lower.startswith("перевести")
    ):
        text_to_translate = re.sub(
            r"^(translate|переведи|перевести)\s*[:,\-]?\s*",
            "",
            user_text.strip(),
            flags=re.IGNORECASE,
        ).strip()
        text_to_translate = re.sub(
            r"^\s*please\s*[:,\-]?\s*", "", text_to_translate, flags=re.IGNORECASE
        ).strip()
        if not text_to_translate or text_to_translate.lower() in {
            "please",
            "pls",
            "plz",
        }:
            return {
                "reply": "Send the text you want me to translate into Russian.",
                "question": None,
                "quick_replies": [],
                "correction": None,
                "tip": None,
            }
        translate_prompt = f"""You are a translator.
Translate the text into Russian. Keep the meaning natural.
Text:
{text_to_translate}
Russian translation:"""
        raw_translation = call_ollama_raw(translate_prompt)
        return {
            "reply": raw_translation,
            "question": None,
            "quick_replies": [],
            "correction": None,
            "tip": None,
        }

    # --- WORD SUGGESTION (оставляем как есть) ---
    suggestion = check_word_and_suggest(user_text)
    if suggestion:
        return {
            "reply": suggestion,
            "question": None,
            "quick_replies": [],
            "correction": None,
            "tip": None,
        }

    # --- CONVERSATION HISTORY ---
    conversation = ""
    if history:
        for role, content in history[-4:]:
            if role == "user":
                conversation += f"\nStudent: {content}"
            else:
                conversation += f"\nTeacher: {content}"

    current_date = datetime.now().strftime("%A, %B %d, %Y")
    LEVEL_STYLE = {
        "A1": "Use very simple words. Short sentences. Ask easy questions. Avoid complex grammar terms.",
        "A2": "Use simple everyday English. Short explanations. One simple follow-up question.",
        "B1": "Use natural English. Give brief corrections. Ask open-ended questions sometimes.",
        "B2": "Use natural fluent English. Correct subtle mistakes. Ask deeper questions.",
    }
    style = LEVEL_STYLE.get(level, LEVEL_STYLE["A1"])

    # ОРИГИНАЛЬНЫЙ ФОРМАТ - весь промпт единым блоком как в Ollama версии
    full_prompt = f"""{SYSTEM_PROMPT}
IMPORTANT: Today's date is {current_date}.
Student level: {level}
Teaching style: {style}
CRITICAL: Check the student's message for ANY grammar, vocabulary, or spelling errors. If you find errors, you MUST provide "correction" field!
Conversation history:{conversation}
Student: {user_text}
Teacher:"""

    raw_response = call_ollama_raw(full_prompt).strip()

    # === ПАРСИНГ JSON ===
    try:
        # Убираем возможные ```json ... ```
        cleaned = raw_response.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned)

        # Валидация ключей
        reply = str(data.get("reply", "")).strip()
        question = data.get("question")
        quick_replies = data.get("quick_replies", [])
        correction = data.get("correction")
        tip = data.get("tip")

        # Очистка quick_replies
        if not isinstance(quick_replies, list):
            quick_replies = []
        quick_replies = [
            str(q).strip() for q in quick_replies if q and len(str(q)) <= 35
        ]
        quick_replies = quick_replies[:4]

        return {
            "reply": reply,
            "question": question,
            "quick_replies": quick_replies,
            "correction": str(correction).strip() if correction else None,
            "tip": str(tip).strip() if tip else None,
        }

    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.error(
            f"Failed to parse LLM JSON response: {e}. Raw: {raw_response[:200]}..."
        )

        # Fallback: вернуть хотя бы текст без структуры
        return {
            "reply": raw_response,
            "question": None,
            "quick_replies": [],
            "correction": None,
            "tip": None,
        }
