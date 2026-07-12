"""
main.py
-------
Entry point aplikasi FastAPI. Menyediakan endpoint:

POST /api/pss10/submit        -> submit jawaban PSS-10, dapat skor awal
POST /api/chat/message         -> kirim pesan ke AI chat (assessment lanjutan)
GET  /api/chat/{assessment_id}/history -> ambil riwayat chat
GET  /api/result/{assessment_id}       -> ambil hasil akhir lengkap
GET  /api/pss10/questions      -> ambil daftar 10 pertanyaan PSS-10
GET  /api/dashboard/stats      -> statistik agregat (untuk demo "dashboard admin")

Jalankan dengan: uvicorn app.main:app --reload
Dokumentasi otomatis tersedia di: http://localhost:8000/docs
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.database import engine, get_db, Base
from app import models, schemas
from app.pss10 import calculate_pss10, PSS10_QUESTIONS, LIKERT_LABELS
from app.ai_chat import get_ai_response
from app.ml_predict import predict_stress, get_feature_list

# Membuat semua tabel di database (jika belum ada) saat aplikasi start
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Student Stress Assessment API",
    description="API untuk mengukur tingkat stress mahasiswa menggunakan PSS-10 + AI Chat Assessment",
    version="1.0.0",
)

# CORS: mengizinkan frontend (file HTML statis / domain lain) mengakses API ini.
# Untuk demo ini dibuka lebar ("*"); untuk production sebaiknya dibatasi ke domain spesifik.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Student Stress Assessment API aktif. Lihat /docs untuk dokumentasi."}


@app.get("/api/pss10/questions")
def get_pss10_questions():
    """Mengambil daftar 10 pertanyaan PSS-10 beserta label skala Likert-nya."""
    return {
        "questions": [
            {"index": i, "text": q} for i, q in enumerate(PSS10_QUESTIONS)
        ],
        "likert_labels": LIKERT_LABELS,
    }


@app.post("/api/pss10/submit", response_model=schemas.PSS10Result)
def submit_pss10(data: schemas.PSS10Submission, db: Session = Depends(get_db)):
    """
    Menerima 10 jawaban PSS-10, menghitung skor, menyimpan ke database,
    dan mengembalikan assessment_id untuk dipakai di sesi chat AI selanjutnya.
    """
    try:
        result = calculate_pss10(data.answers)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    assessment = models.Assessment(
        nama=data.nama,
        jurusan=data.jurusan,
        pss_answers=data.answers,
        pss_score=result["total_score"],
        pss_category=result["category"],
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return schemas.PSS10Result(
        assessment_id=assessment.id,
        total_score=result["total_score"],
        max_score=result["max_score"],
        category=result["category"],
    )


@app.post("/api/chat/message", response_model=schemas.ChatReply)
def send_chat_message(data: schemas.ChatMessageIn, db: Session = Depends(get_db)):
    """
    Mengirim satu pesan dari mahasiswa ke AI, menyimpan riwayat percakapan,
    dan jika AI sudah cukup informasi, otomatis menyimpan hasil penyesuaian skor.
    """
    assessment = db.query(models.Assessment).filter(
        models.Assessment.id == data.assessment_id
    ).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment tidak ditemukan")

    # Simpan pesan user
    user_msg = models.ChatMessage(
        assessment_id=assessment.id, role="user", content=data.message
    )
    db.add(user_msg)
    db.commit()

    # Ambil seluruh riwayat percakapan untuk dikirim sebagai context ke AI
    history = db.query(models.ChatMessage).filter(
        models.ChatMessage.assessment_id == assessment.id
    ).order_by(models.ChatMessage.id).all()

    conversation = [{"role": m.role, "content": m.content} for m in history]

    try:
        ai_result = get_ai_response(
            conversation_history=conversation,
            pss_score=assessment.pss_score,
            pss_category=assessment.pss_category,
        )
    except Exception as e:
        print(f"[ERROR] get_ai_response gagal: {e}")
        ai_result = {
            "reply": (
                "Maaf, AI chat sedang tidak tersedia saat ini. "
                "Coba lagi beberapa saat lagi, atau lanjutkan hasil tanpa chat." 
            ),
            "is_complete": False,
            "result_data": None,
        }

    # Simpan balasan AI
    ai_msg = models.ChatMessage(
        assessment_id=assessment.id, role="assistant", content=ai_result["reply"]
    )
    db.add(ai_msg)

    # Jika AI sudah menghasilkan skor final, simpan ke tabel assessment
    if ai_result["is_complete"] and ai_result["result_data"]:
        rd = ai_result["result_data"]
        assessment.ai_adjusted_score = rd.get("adjusted_score")
        assessment.ai_adjusted_category = rd.get("category")
        assessment.ai_summary = rd.get("summary")
        assessment.ai_recommendation = rd.get("recommendation")

    db.commit()

    return schemas.ChatReply(
        reply=ai_result["reply"],
        is_assessment_complete=ai_result["is_complete"],
    )


@app.get("/api/chat/{assessment_id}/history", response_model=List[schemas.ChatMessageOut])
def get_chat_history(assessment_id: int, db: Session = Depends(get_db)):
    """Mengambil seluruh riwayat chat untuk satu assessment."""
    assessment = db.query(models.Assessment).filter(
        models.Assessment.id == assessment_id
    ).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment tidak ditemukan")

    history = db.query(models.ChatMessage).filter(
        models.ChatMessage.assessment_id == assessment_id
    ).order_by(models.ChatMessage.id).all()

    return history


@app.get("/api/result/{assessment_id}", response_model=schemas.FinalResult)
def get_final_result(assessment_id: int, db: Session = Depends(get_db)):
    """Mengambil hasil akhir lengkap (skor PSS-10 + hasil penyesuaian AI jika sudah ada)."""
    assessment = db.query(models.Assessment).filter(
        models.Assessment.id == assessment_id
    ).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment tidak ditemukan")

    # Dibentuk secara eksplisit (bukan return langsung object SQLAlchemy) karena
    # nama kolom di database adalah "id", sedangkan schema response memakai
    # nama field "assessment_id" - auto-konversi FastAPI tidak bisa memetakan
    # nama yang berbeda ini, jadi perlu dipetakan manual di sini.
    return schemas.FinalResult(
        assessment_id=assessment.id,
        nama=assessment.nama,
        jurusan=assessment.jurusan,
        pss_score=assessment.pss_score,
        pss_category=assessment.pss_category,
        ai_adjusted_score=assessment.ai_adjusted_score,
        ai_adjusted_category=assessment.ai_adjusted_category,
        ai_summary=assessment.ai_summary,
        ai_recommendation=assessment.ai_recommendation,
        created_at=assessment.created_at,
    )


@app.get("/api/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Statistik agregat sederhana - cocok untuk ditampilkan di 'dashboard admin'
    saat demo pameran (menunjukkan distribusi tingkat stress seluruh responden).
    """
    total = db.query(func.count(models.Assessment.id)).scalar() or 0

    by_category = (
        db.query(models.Assessment.pss_category, func.count(models.Assessment.id))
        .group_by(models.Assessment.pss_category)
        .all()
    )

    avg_score = db.query(func.avg(models.Assessment.pss_score)).scalar()

    return {
        "total_responden": total,
        "rata_rata_skor_pss": round(avg_score, 2) if avg_score else 0,
        "distribusi_kategori": {cat: count for cat, count in by_category},
    }


@app.get("/api/ml/features")
def get_ml_features():
    """
    Mengembalikan daftar fitur yang dibutuhkan model Random Forest.
    Berguna untuk frontend membangun form input ML secara dinamis.
    """
    return {"features": get_feature_list()}


@app.post("/api/chat/finalize/{assessment_id}")
def finalize_assessment(assessment_id: int, db: Session = Depends(get_db)):
    """
    Endpoint khusus untuk memaksa AI generate hasil akhir (JSON) dari
    seluruh riwayat percakapan yang sudah ada — dipanggil saat user
    klik tombol 'Lihat Hasil Akhir' di frontend.

    Berbeda dengan /api/chat/message biasa, endpoint ini menyisipkan
    instruksi eksplisit di akhir riwayat chat supaya AI LANGSUNG
    mengeluarkan blok JSON tanpa teks panjang sebelumnya.
    """
    assessment = db.query(models.Assessment).filter(
        models.Assessment.id == assessment_id
    ).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment tidak ditemukan")

    # Kalau sudah ada hasil AI sebelumnya, langsung return tanpa panggil AI lagi
    if assessment.ai_adjusted_score is not None:
        return {"status": "already_complete"}

    history = db.query(models.ChatMessage).filter(
        models.ChatMessage.assessment_id == assessment_id
    ).order_by(models.ChatMessage.id).all()

    conversation = [{"role": m.role, "content": m.content} for m in history]

    # Tambahkan perintah eksplisit sebagai pesan user terakhir
    finalize_instruction = (
        "Based on the entire conversation, please provide the final assessment now. "
        "Write ONLY the JSON block below with no extra text before or after:\n\n"
        "```json\n"
        "{\n"
        "  \"assessment_complete\": true,\n"
        "  \"adjusted_score\": <number 0-100>,\n"
        "  \"category\": \"<Low|Moderate|High>\",\n"
        "  \"summary\": \"<brief 2-3 sentence summary>\",\n"
        "  \"recommendation\": \"<2-4 sentence recommendation>\"\n"
        "}\n"
        "```"
    )

    conversation.append({"role": "user", "content": finalize_instruction})

    ai_result = get_ai_response(
        conversation_history=conversation,
        pss_score=assessment.pss_score,
        pss_category=assessment.pss_category,
    )

    if ai_result["is_complete"] and ai_result["result_data"]:
        rd = ai_result["result_data"]
        assessment.ai_adjusted_score = rd.get("adjusted_score")
        assessment.ai_adjusted_category = rd.get("category")
        assessment.ai_summary = rd.get("summary")
        assessment.ai_recommendation = rd.get("recommendation")

        # Simpan pesan finalize ke riwayat chat
        db.add(models.ChatMessage(
            assessment_id=assessment_id,
            role="assistant",
            content=ai_result["reply"] or "Hasil penilaian telah dibuat."
        ))
        db.commit()
        return {"status": "complete"}
    else:
        raise HTTPException(
            status_code=500,
            detail="AI gagal menghasilkan penilaian akhir. Coba lagi."
        )


@app.post("/api/ml/predict")
def ml_predict(feature_values: dict):
    """
    Memprediksi tingkat stress menggunakan model Random Forest
    yang dilatih dari dataset StressLevelDataset (Kaggle).

    Menerima: dict berisi nilai-nilai fitur (anxiety_level, sleep_quality, dll)
    Mengembalikan: prediksi kategori stress + confidence + probabilitas per kelas

    Akurasi model: 88.18% pada test set, 87.36% cross-validation (5-fold)
    """
    try:
        result = predict_stress(feature_values)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Prediksi gagal: {str(e)}")

