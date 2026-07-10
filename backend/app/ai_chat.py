"""
ai_chat.py
----------
AI Chat dalam mode SUPPORTIF — bukan assessment.

Alur baru:
- Hasil PSS-10 dan ML sudah ditampilkan langsung ke user
- Chat AI hanya sebagai ruang curhat dan dukungan emosional
- AI tidak perlu generate JSON assessment lagi
- Kalau ada indikasi stress tinggi dari cerita user, AI bisa
  menyarankan untuk melihat ulang hasil atau hubungi konseling

Provider: Groq (utama) → Gemini (fallback otomatis)
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

SYSTEM_PROMPT = """Anda adalah teman AI yang hangat dan empatik dalam aplikasi Stressgraph.
Pengguna adalah mahasiswa yang sudah menyelesaikan pengukuran stress (PSS-10 dan Machine Learning).
Hasil pengukuran sudah ditampilkan — tugas Anda BUKAN mengukur atau menilai ulang, melainkan:

1. MENDENGARKAN dengan tulus — biarkan mahasiswa bercerita apapun yang mereka rasakan
2. MERESPONS dengan empati — validasi perasaan mereka tanpa menghakimi
3. MEMBERI DUKUNGAN ringan — tips sederhana, perspektif positif, atau sekadar menemani
4. MENGARAHKAN ke profesional jika diperlukan — kalau cerita menunjukkan tekanan berat

ATURAN:
- Gunakan Bahasa Indonesia yang hangat, santai, dan natural — seperti teman bicara
- JANGAN mendiagnosis kondisi klinis apapun
- JANGAN mengulang atau membahas angka skor kecuali ditanya
- Jika mahasiswa menyebut krisis (menyakiti diri, ingin mati):
  HENTIKAN percakapan biasa, sampaikan empati, dan DENGAN TEGAS arahkan ke
  Layanan Sejiwa 119 ext 8 atau konseling kampus — ini prioritas utama
- Respons cukup 2-4 kalimat — tidak perlu panjang, yang penting tulus
- JANGAN generate blok JSON apapun — ini bukan sesi assessment
"""


def _fallback_response(conversation_history: list, pss_score: int, pss_category: str) -> str:
    """Respons lokal saat provider AI eksternal tidak tersedia."""
    return (
        f"Saya mendengar kamu sedang merasa terbebani. Hasil PSS-10 menunjukkan tingkat stress {pss_category.lower()}, "
        "tapi yang paling penting adalah apa yang kamu rasakan sekarang. "
        "Ceritakan saja apa yang membuat kamu stres, dan saya akan mendukung dengan empati. "
        "Kalau kamu merasa sangat tertekan, coba juga hubungi konselor kampus atau orang terpercaya."
    )


def _is_groq_available() -> bool:
    return Groq is not None and bool(GROQ_API_KEY)


def _is_gemini_available() -> bool:
    return genai is not None and types is not None and bool(GEMINI_API_KEY)


def _make_groq_client():
    if not _is_groq_available():
        raise RuntimeError(
            "Groq client tidak tersedia. Pastikan package 'groq' terpasang dan GROQ_API_KEY diset di backend/.env."
        )
    return Groq(api_key=GROQ_API_KEY)


def _make_gemini_client():
    if not _is_gemini_available():
        raise RuntimeError(
            "Gemini client tidak tersedia. Pastikan package 'google-genai' terpasang dan GEMINI_API_KEY diset di backend/.env."
        )
    return genai.Client(api_key=GEMINI_API_KEY)


def call_groq(conversation_history: list, pss_score: int, pss_category: str) -> str:
    """Panggil Groq API, return teks respons."""
    if not _is_groq_available():
        raise RuntimeError("Groq provider tidak siap.")

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
    """Panggil Gemini API, return teks respons."""
    if not _is_gemini_available():
        raise RuntimeError("Gemini provider tidak siap.")

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
    Kirim pesan ke AI supportif dengan fallback Groq → Gemini.
    Return dict: {"reply": str, "is_complete": False, "result_data": None}
    """
    providers = []
    if _is_groq_available():
        providers.append(("Groq", call_groq))
    if _is_gemini_available():
        providers.append(("Gemini (fallback)", call_gemini))

    if not providers:
        print("[WARN] Tidak ada provider AI eksternal tersedia, menggunakan respons lokal fallback.")
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
                print(f"[INFO] Mencoba {provider_name} (percobaan {attempt + 1}/{MAX_RETRIES})...")

            reply = provider_fn(conversation_history, pss_score, pss_category)
            if not reply or not reply.strip():
                raise RuntimeError(f"{provider_name} mengembalikan respons kosong.")

            if attempt > 0:
                print(f"[OK] Berhasil via {provider_name}.")

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
                print(f"[INFO] Tunggu {delay}s lalu retry...")
                time.sleep(delay)
                continue

            if len(providers) > 1 and provider_name != providers[-1][0] and attempt == MAX_RETRIES - 1:
                continue

            break

    print("[WARN] Semua provider AI gagal, menggunakan respons lokal fallback.")
    return {
        "reply": _fallback_response(conversation_history, pss_score, pss_category),
        "is_complete": False,
        "result_data": None,
    }
