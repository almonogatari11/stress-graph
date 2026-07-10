"""
train_model.py
--------------
Script untuk melatih model Random Forest dari dataset StressLevelDataset.csv

Cara menjalankan:
  python train_model.py

Output:
  - app/stress_model.pkl       (model terlatih)
  - app/stress_model_features.pkl  (daftar fitur)
  - hasil evaluasi akurasi di terminal

Dataset yang dipakai:
  StressLevelDataset.csv (1100 baris, 20 fitur + 1 label stress_level)
  Sumber: kaggle.com/datasets/rxnach/student-stress-factors-a-comprehensive-analysis
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import os

DATASET_PATH = "StressLevelDataset.csv"
MODEL_OUTPUT  = "app/stress_model.pkl"
FEATURES_OUTPUT = "app/stress_model_features.pkl"
LABEL_MAP = {0: "Rendah", 1: "Sedang", 2: "Tinggi"}

def train():
    print("=" * 50)
    print("Training Model Random Forest - Stress Detection")
    print("=" * 50)

    if not os.path.exists(DATASET_PATH):
        print(f"ERROR: File {DATASET_PATH} tidak ditemukan!")
        print("Letakkan file CSV di folder yang sama dengan script ini.")
        return

    df = pd.read_csv(DATASET_PATH)
    print(f"Dataset loaded: {df.shape[0]} baris, {df.shape[1]} kolom")
    print(f"Distribusi label: {df['stress_level'].value_counts().to_dict()}")

    X = df.drop("stress_level", axis=1)
    y = df["stress_level"]
    features = list(X.columns)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\nTraining set: {len(X_train)} | Test set: {len(X_test)}")

    print("\nMelatih model Random Forest (100 trees)...")
    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight="balanced"
    )
    model.fit(X_train, y_train)

    # Evaluasi
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nAkurasi Test Set : {acc*100:.2f}%")

    cv = cross_val_score(model, X, y, cv=5)
    print(f"Cross-Validation : {cv.mean()*100:.2f}% ± {cv.std()*100:.2f}%")

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred,
          target_names=[LABEL_MAP[i] for i in sorted(LABEL_MAP)]))

    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    # Feature importance
    importances = pd.Series(model.feature_importances_, index=features)
    importances = importances.sort_values(ascending=False)
    print("\nTop 5 Fitur Paling Berpengaruh:")
    for feat, imp in importances.head(5).items():
        print(f"  {feat}: {imp:.4f}")

    # Simpan model
    joblib.dump(model, MODEL_OUTPUT)
    joblib.dump(features, FEATURES_OUTPUT)
    print(f"\nModel disimpan ke: {MODEL_OUTPUT}")
    print(f"Features disimpan ke: {FEATURES_OUTPUT}")
    print("\nTraining selesai!")

if __name__ == "__main__":
    train()
