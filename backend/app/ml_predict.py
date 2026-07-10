"""
ml_predict.py
-------------
Modul untuk memuat model Random Forest yang sudah dilatih
dan melakukan prediksi tingkat stress berdasarkan fitur dari
dataset StressLevelDataset.csv (Kaggle).

Fitur yang dipakai (20 fitur, urutan harus sama persis dengan saat training):
anxiety_level, self_esteem, mental_health_history, depression, headache,
blood_pressure, sleep_quality, breathing_problem, noise_level, living_conditions,
safety, basic_needs, academic_performance, study_load, teacher_student_relationship,
future_career_concerns, social_support, peer_pressure, extracurricular_activities,
bullying

Label output:
  0 = Rendah
  1 = Sedang
  2 = Tinggi

Akurasi model: 88.18% (test set 20%), Cross-validation: 87.36% ± 2.39%
"""

import os
import joblib
import numpy as np

# Path relatif ke file model (ada di folder yang sama dengan file ini)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "stress_model.pkl")
FEATURES_PATH = os.path.join(BASE_DIR, "stress_model_features.pkl")

# Load model saat modul pertama kali diimport (tidak perlu load ulang tiap request)
_model = joblib.load(MODEL_PATH)
_features = joblib.load(FEATURES_PATH)

LABEL_MAP = {0: "Rendah", 1: "Sedang", 2: "Tinggi"}


def predict_stress(feature_values: dict) -> dict:
    """
    Memprediksi tingkat stress dari dictionary fitur.

    Args:
        feature_values: dict dengan key nama fitur dan value angkanya.
                        Fitur yang tidak ada akan diisi 0 (default).

    Returns:
        dict berisi:
          - predicted_label: int (0/1/2)
          - predicted_category: str ("Rendah"/"Sedang"/"Tinggi")
          - confidence: float (probabilitas prediksi, 0-100)
          - probabilities: dict {Rendah: %, Sedang: %, Tinggi: %}
    """
    # Susun input sesuai urutan fitur saat training
    input_vector = np.array([[feature_values.get(f, 0) for f in _features]])

    predicted_label = int(_model.predict(input_vector)[0])
    proba = _model.predict_proba(input_vector)[0]

    return {
        "predicted_label": predicted_label,
        "predicted_category": LABEL_MAP[predicted_label],
        "confidence": round(float(proba[predicted_label]) * 100, 1),
        "probabilities": {
            "Rendah": round(float(proba[0]) * 100, 1),
            "Sedang": round(float(proba[1]) * 100, 1),
            "Tinggi": round(float(proba[2]) * 100, 1),
        }
    }


def get_feature_list() -> list:
    """Mengembalikan daftar nama fitur yang dibutuhkan model."""
    return _features
