"""
database.py
------------
Mengatur koneksi ke database SQLite menggunakan SQLAlchemy.
SQLite dipilih karena tidak perlu instalasi server database terpisah -
cukup 1 file (stress_app.db) yang otomatis dibuat saat aplikasi pertama dijalankan.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./stress_app.db")

# check_same_thread=False diperlukan khusus untuk SQLite agar bisa diakses
# dari beberapa request FastAPI secara bersamaan.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependency untuk FastAPI - membuka session database per-request
    dan menutupnya otomatis setelah selesai (lihat: Depends(get_db) di routes).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
