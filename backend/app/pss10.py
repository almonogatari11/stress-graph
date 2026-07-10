"""
pss10.py
--------
Implementasi Perceived Stress Scale - 10 item (PSS-10), dikembangkan oleh
Cohen, Kamarck, & Mermelstein (1983/1988). Ini instrumen self-report yang
banyak dipakai secara internasional untuk mengukur "perceived stress"
(persepsi seseorang terhadap level stress dalam 1 bulan terakhir).

CARA SKORING (penting, sering salah jika dibuat tanpa rujukan):
- 10 pertanyaan, masing-masing dijawab dengan skala 0-4:
    0 = Tidak Pernah
    1 = Hampir Tidak Pernah
    2 = Kadang-kadang
    3 = Sering
    4 = Sangat Sering

- 4 pertanyaan adalah "POSITIVE ITEMS" dan harus DIBALIK (reverse-scored)
  sebelum dijumlah, yaitu pertanyaan nomor: 4, 5, 7, 8 (index 3, 4, 6, 7
  jika dihitung dari 0). Pertanyaan ini bersifat positif (mis. "merasa
  mampu mengendalikan"), sehingga skor tinggi di sini = stress LEBIH RENDAH,
  maka harus dibalik agar konsisten dengan item lain.

  Rumus reverse: skor_baru = 4 - skor_asli

- Total skor = 0 - 40, kategori umum yang dipakai banyak studi:
    0–13   = Stress Rendah
    14–26  = Stress Sedang
    27–40  = Stress Tinggi

Sumber: Cohen, S., Kamarck, T., & Mermelstein, R. (1983).
"A global measure of perceived stress." Journal of Health and Social Behavior.
"""

from typing import List, Dict

# Index pertanyaan (0-based) yang harus di-reverse-score
REVERSE_SCORED_INDEXES = [3, 4, 6, 7]  # = pertanyaan nomor 4, 5, 7, 8

PSS10_QUESTIONS = [
    "Dalam satu bulan terakhir, seberapa sering Anda merasa terganggu karena sesuatu yang terjadi secara tidak terduga?",
    "Dalam satu bulan terakhir, seberapa sering Anda merasa tidak mampu mengontrol hal-hal penting dalam hidup Anda?",
    "Dalam satu bulan terakhir, seberapa sering Anda merasa gelisah dan tertekan (stress)?",
    "Dalam satu bulan terakhir, seberapa sering Anda merasa yakin mampu menangani masalah-masalah pribadi Anda dengan baik?",
    "Dalam satu bulan terakhir, seberapa sering Anda merasa bahwa hal-hal berjalan sesuai keinginan Anda?",
    "Dalam satu bulan terakhir, seberapa sering Anda merasa tidak dapat mengatasi semua hal yang harus Anda lakukan?",
    "Dalam satu bulan terakhir, seberapa sering Anda mampu mengendalikan rasa mudah marah/tersinggung dalam hidup Anda?",
    "Dalam satu bulan terakhir, seberapa sering Anda merasa berada di puncak (mampu menguasai keadaan)?",
    "Dalam satu bulan terakhir, seberapa sering Anda merasa marah karena hal-hal yang terjadi di luar kendali Anda?",
    "Dalam satu bulan terakhir, seberapa sering Anda merasa kesulitan menumpuk sedemikian banyak sehingga Anda tidak dapat mengatasinya?",
]

LIKERT_LABELS = [
    "Tidak Pernah",
    "Hampir Tidak Pernah",
    "Kadang-kadang",
    "Sering",
    "Sangat Sering",
]


def calculate_pss10(answers: List[int]) -> Dict:
    """
    Menghitung skor PSS-10 dari 10 jawaban (masing-masing 0-4).

    Args:
        answers: list berisi 10 integer, masing-masing 0-4,
                 sesuai urutan PSS10_QUESTIONS.

    Returns:
        dict berisi: total_score, category, dan detail per-item (untuk transparansi/debug)
    """
    if len(answers) != 10:
        raise ValueError(f"PSS-10 membutuhkan tepat 10 jawaban, diterima: {len(answers)}")

    for i, ans in enumerate(answers):
        if not (0 <= ans <= 4):
            raise ValueError(f"Jawaban index {i} harus antara 0-4, diterima: {ans}")

    adjusted_scores = []
    for i, ans in enumerate(answers):
        if i in REVERSE_SCORED_INDEXES:
            adjusted_scores.append(4 - ans)
        else:
            adjusted_scores.append(ans)

    total_score = sum(adjusted_scores)
    category = categorize_pss_score(total_score)

    return {
        "total_score": total_score,
        "max_score": 40,
        "category": category,
        "raw_answers": answers,
        "adjusted_scores": adjusted_scores,
    }


def categorize_pss_score(score: int) -> str:
    """Mengkategorikan skor PSS-10 total (0-40) ke dalam 3 level."""
    if score <= 13:
        return "Rendah"
    elif score <= 26:
        return "Sedang"
    else:
        return "Tinggi"
