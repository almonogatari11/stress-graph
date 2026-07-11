"""
ai_chat.py
----------
AI chat in supportive mode — not for assessment.

New flow:
- PSS-10 and ML results are already displayed to the user
- The AI chat is only for emotional support and listening
- The AI does not need to generate assessment JSON
- If there are signs of high stress from the user's story, the AI can
  suggest reviewing the results or contacting counseling

Provider: Groq (primary) → Gemini (automatic fallback)
"""

import os
import time

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except Exception:
    load_dotenv = None
    DOTENV_AVAILABLE = False

# Pastikan .env dimuat dari folder backend, bukan hanya dari cwd saat startup.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
if DOTENV_AVAILABLE:
    load_dotenv(ENV_PATH)
elif os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.5-flash"

try:
    from groq import Groq
except Exception as e:
    Groq = None
    GROQ_IMPORT_ERROR = e
    print(f"[WARN] Groq import gagal: {e}")

try:
    from google import genai
    from google.genai import types
except Exception as e:
    genai = None
    types = None
    GEMINI_IMPORT_ERROR = e
    print(f"[WARN] Gemini import gagal: {e}")

SYSTEM_PROMPT = """You are a warm, empathetic AI companion inside the Stressgraph application.
The user is a student who has completed stress measurement (PSS-10 and Machine Learning).
Results are already visible — your role is NOT to reassess, but to provide supportive conversation:

1. LISTEN with genuine attention — let the student share their feelings
2. RESPOND with empathy — validate feelings without judgment
3. OFFER light support — simple coping tips, perspective, or a supportive presence
4. GUIDE to professionals if necessary — if signs of severe distress appear

RULES:
- Use natural, conversational English with a supportive tone
- DO NOT diagnose clinical conditions
- DO NOT repeat or analyze numeric scores unless asked
- If the user mentions crisis (self-harm or suicidal intent):
    STOP regular conversation, show empathy, and URGENTLY direct them to local crisis services or campus counseling
- Keep replies short (2-4 sentences) and compassionate
- DO NOT produce machine-readable JSON — this is a supportive chat only
"""


def _fallback_response(conversation_history: list, pss_score: int, pss_category: str) -> str:
    """Local fallback response when external AI providers are not available."""
    return (
        f"I hear that you're feeling burdened. The PSS-10 result indicates a {pss_category.lower()} level, "
        "but what matters most is how you feel right now. "
        "Tell me what's making you stressed, and I'll respond with empathy and practical support. "
        "If you feel in immediate danger or very distressed, please contact campus counseling or local crisis services."
    )


def _is_groq_available() -> bool:
    return Groq is not None and bool(GROQ_API_KEY)


def _is_gemini_available() -> bool:
    return genai is not None and types is not None and bool(GEMINI_API_KEY)


def _make_groq_client():
    if not _is_groq_available():
        raise RuntimeError(
            "Groq client is unavailable. Make sure the 'groq' package is installed and GROQ_API_KEY is set in backend/.env."
        )
    return Groq(api_key=GROQ_API_KEY)


def _make_gemini_client():
    if not _is_gemini_available():
        raise RuntimeError(
            "Gemini client is unavailable. Make sure the 'google-genai' package is installed and GEMINI_API_KEY is set in backend/.env."
        )
    return genai.Client(api_key=GEMINI_API_KEY)


def call_groq(conversation_history: list, pss_score: int, pss_category: str) -> str:
    """Call the Groq API and return the response text."""
    if not _is_groq_available():
        raise RuntimeError("Groq provider is not ready.")

    groq_client = _make_groq_client()
    context = (
        f"[INFO: Skor PSS-10 mahasiswa ini {pss_score}/40, kategori {pss_category}. "
        f"Gunakan ini hanya sebagai latar belakang, jangan dibahas kecuali ditanya.]"
    )
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for i, msg in enumerate(conversation_history):
        content = msg["content"]
        if i == 0 and msg["role"] == "user":
            content = context + "\n\n" + content
        messages.append({"role": msg["role"], "content": content})

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=512,
        temperature=0.8,
    )
    return response.choices[0].message.content or ""


def call_gemini(conversation_history: list, pss_score: int, pss_category: str) -> str:
    """Call the Gemini API and return the response text."""
    if not _is_gemini_available():
        raise RuntimeError("Gemini provider is not ready.")

    gemini_client = _make_gemini_client()
    context = (
        f"[INFO: Skor PSS-10 mahasiswa ini {pss_score}/40, kategori {pss_category}. "
        f"Gunakan hanya sebagai latar belakang.]"
    )
    contents = []
    for i, msg in enumerate(conversation_history):
        content = msg["content"]
        if i == 0 and msg["role"] == "user":
            content = context + "\n\n" + content
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=content)])
        )

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        max_output_tokens=512,
    )
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=config,
    )
    return response.text or ""


def get_ai_response(conversation_history: list, pss_score: int, pss_category: str):
    """
    Send a message to the supportive AI with Groq → Gemini fallback.
    Return dict: {"reply": str, "is_complete": False, "result_data": None}
    """
    providers = []
    if _is_groq_available():
        providers.append(("Groq", call_groq))
    if _is_gemini_available():
        providers.append(("Gemini (fallback)", call_gemini))

    if not providers:
        print("[WARN] No external AI providers available, using local fallback response.")
        return {
            "reply": _fallback_response(conversation_history, pss_score, pss_category),
            "is_complete": False,
            "result_data": None,
        }

    MAX_RETRIES = 3
    RETRY_DELAYS = [3, 5, 10]
    last_error = None

    for attempt in range(MAX_RETRIES):
        use_gemini = len(providers) > 1 and attempt >= MAX_RETRIES - 1
        provider_name, provider_fn = providers[1] if use_gemini else providers[0]

        try:
            if attempt > 0:
                print(f"[INFO] Trying {provider_name} (attempt {attempt + 1}/{MAX_RETRIES})...")

            reply = provider_fn(conversation_history, pss_score, pss_category)
            if not reply or not reply.strip():
                raise RuntimeError(f"{provider_name} returned an empty response.")

            if attempt > 0:
                print(f"[OK] Successful via {provider_name}.")

            return {
                "reply": reply,
                "is_complete": False,
                "result_data": None,
            }

        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            is_retryable = any(x in err_str for x in ["503", "429", "rate", "overload", "unavailable"])
            print(f"[WARN] {provider_name} error: {str(e)[:200]}")

            if attempt < MAX_RETRIES - 1 and is_retryable:
                delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                print(f"[INFO] Waiting {delay}s then retrying...")
                time.sleep(delay)
                continue

            if len(providers) > 1 and provider_name != providers[-1][0] and attempt == MAX_RETRIES - 1:
                continue

            break

    print("[WARN] All AI providers failed, using local fallback response.")
    return {
        "reply": _fallback_response(conversation_history, pss_score, pss_category),
        "is_complete": False,
        "result_data": None,
    }
