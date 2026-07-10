"""
schemas.py
----------
Pydantic models untuk validasi data masuk (request) dan keluar (response) di API.
FastAPI otomatis menggunakan ini untuk validasi + dokumentasi Swagger (/docs).
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# ---------- PSS-10 ----------

class PSS10Submission(BaseModel):
    nama: Optional[str] = Field(None, description="Nama mahasiswa (opsional)")
    jurusan: Optional[str] = Field(None, description="Jurusan/program studi (opsional)")
    answers: List[int] = Field(
        ...,
        min_length=10,
        max_length=10,
        description="10 jawaban PSS-10, masing-masing bernilai 0-4"
    )


class PSS10Result(BaseModel):
    assessment_id: int
    total_score: int
    max_score: int
    category: str


# ---------- AI Chat ----------

class ChatMessageIn(BaseModel):
    assessment_id: int
    message: str = Field(..., min_length=1, max_length=2000)


class ChatMessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime


class ChatReply(BaseModel):
    reply: str
    is_assessment_complete: bool = Field(
        False,
        description="True jika AI sudah mengumpulkan cukup info dan menghasilkan skor final"
    )


# ---------- Hasil Akhir ----------

class FinalResult(BaseModel):
    assessment_id: int
    nama: Optional[str]
    jurusan: Optional[str]
    pss_score: int
    pss_category: str
    ai_adjusted_score: Optional[float]
    ai_adjusted_category: Optional[str]
    ai_summary: Optional[str]
    ai_recommendation: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
