"""
Quick training script to generate the legacy insulin_system inference bundle.

This project’s API can run in two modes:
1) Smart Sensor pipeline (preferred) if outputs/smart_sensor_ml/model_bundle/bundle.joblib exists
2) Legacy insulin_system pipeline (fallback) which requires outputs/best_model/inference_bundle.joblib

In some checkouts the legacy bundle is missing, causing /api/recommend to return HTTP 503.
This script generates a lightweight, deterministic bundle from synthetic-but-plausible data
so the API can start and serve recommendations immediately for demos/dev.
"""

from __future__ import annotations

import random
from pathlib import Path

import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder, StandardScaler

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = REPO_ROOT / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from insulin_system.config.schema import DataSchema
from insulin_system.persistence.bundle import NotebookInferenceBundle, save_best_model


def _label_from_glucose(gl: float) -> str:
    # Simple clinical-ish heuristic for a demo classifier.
    if gl < 70:
        return "down"
    if gl > 180:
        return "up"
    if 90 <= gl <= 110:
        return "no"
    return "steady"


def main() -> int:
    random.seed(42)
    np.random.seed(42)

    schema = DataSchema()
    out_dir = Path("outputs/best_model")
    out_dir.mkdir(parents=True, exist_ok=True)

    n = 2500
    genders = ["male", "female"]
    family = ["yes", "no"]
    food = ["low", "medium", "high"]
    prev = ["none", "oral", "insulin"]
    trends = ["stable", "rising", "falling"]

    df = pd.DataFrame(
        {
            schema.PATIENT_ID: np.arange(1, n + 1),
            "gender": np.random.choice(genders, size=n),
            "family_history": np.random.choice(family, size=n),
            "food_intake": np.random.choice(food, size=n),
            "previous_medications": np.random.choice(prev, size=n),
            "age": np.random.randint(18, 85, size=n),
            "glucose_level": np.clip(np.random.normal(140, 55, size=n), 40, 500),
            "physical_activity": np.clip(np.random.normal(4, 3, size=n), 0, 15),
            "BMI": np.clip(np.random.normal(27, 6, size=n), 14, 55),
            "HbA1c": np.clip(np.random.normal(7.2, 1.5, size=n), 4.5, 14.5),
            "weight": np.clip(np.random.normal(78, 18, size=n), 35, 180),
            "insulin_sensitivity": np.clip(np.random.normal(1.0, 0.25, size=n), 0.2, 2.5),
            "sleep_hours": np.clip(np.random.normal(7, 1.3, size=n), 3, 11),
            "creatinine": np.clip(np.random.normal(1.0, 0.25, size=n), 0.3, 2.5),
            "iob": np.clip(np.random.normal(0.02, 0.02, size=n), 0.0, 0.2),
            "anticipated_carbs": np.clip(np.random.normal(15, 25, size=n), 0.0, 150.0),
            "glucose_trend": np.random.choice(trends, size=n),
        }
    )

    df[schema.TARGET] = df["glucose_level"].apply(_label_from_glucose)

    # Encode categoricals and target.
    label_encoders: dict[str, LabelEncoder] = {}
    for col in [
        "gender",
        "family_history",
        "food_intake",
        "previous_medications",
        "glucose_trend",
        schema.TARGET,
    ]:
        le = LabelEncoder()
        le.fit(df[col].astype(str))
        label_encoders[col] = le

    # Prepare training matrix from raw df (NotebookInferenceBundle mirrors this transform).
    feat_cols = [
        "gender",
        "family_history",
        "food_intake",
        "previous_medications",
        "age",
        "glucose_level",
        "physical_activity",
        "BMI",
        "HbA1c",
        "weight",
        "insulin_sensitivity",
        "sleep_hours",
        "creatinine",
        "iob",
        "anticipated_carbs",
        "glucose_trend",
    ]
    X_df = df[feat_cols].copy()
    for c in ["gender", "family_history", "food_intake", "previous_medications", "glucose_trend"]:
        X_df[c] = label_encoders[c].transform(X_df[c].astype(str))
    X = X_df.astype(np.float64).values
    y = label_encoders[schema.TARGET].transform(df[schema.TARGET].astype(str))

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    clf = LogisticRegression(max_iter=1500, multi_class="auto")
    clf.fit(Xs, y)

    bundle = NotebookInferenceBundle(
        model=clf,
        scaler=scaler,
        label_encoders=label_encoders,
        feature_names=feat_cols,
        model_name="quick_demo_logreg",
        metric_name="synthetic_demo",
        metric_value=0.0,
    )
    save_best_model(bundle, output_dir=out_dir, versioned=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

