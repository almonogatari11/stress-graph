"""
models.py
---------
Mendefinisikan struktur tabel database:

1. Assessment   -> satu sesi pengukuran stress (1 mahasiswa, 1x pengisian PSS-10 + chat AI)
2. ChatMessage  -> riwayat percakapan dengan AI untuk satu assessment tertentu

Desain ini sengaja dibuat sederhana (tanpa sistem login/auth) karena tujuannya
untuk demo pameran. Identitas mahasiswa hanya nama + (opsional) NIM/jurusan,
TANPA data sensitif lain.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)

    # Identitas dasar (opsional, tidak ada data sensitif)
    nama = Column(String, nullable=True)
    jurusan = Column(String, nullable=True)

    # Jawaban mentah PSS-10 (10 angka 0-4), disimpan sebagai JSON list
    pss_answers = Column(JSON, nullable=False)

    # Hasil skoring PSS-10 standar
    pss_score = Column(Integer, nullable=False)          # total skor 0-40
    pss_category = Column(String, nullable=False)        # "Rendah" / "Sedang" / "Tinggi"

    # Hasil setelah AI chat menyesuaikan/memperkaya skor PSS
    ai_adjusted_score = Column(Float, nullable=True)      # skor final 0-100 (dinormalisasi)
    ai_adjusted_category = Column(String, nullable=True)
    ai_summary = Column(Text, nullable=True)              # ringkasan analisis AI
    ai_recommendation = Column(Text, nullable=True)       # rekomendasi dari AI

    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("ChatMessage", back_populates="assessment", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)

    role = Column(String, nullable=False)   # "user" atau "assistant"
    content = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    assessment = relationship("Assessment", back_populates="messages")
