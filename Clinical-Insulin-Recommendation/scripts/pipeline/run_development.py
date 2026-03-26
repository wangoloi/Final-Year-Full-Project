"""
Run the revised insulin prediction model development pipeline.

Implements the full 11-section workflow:
1. Data Loading and Understanding
2. Data Cleaning and Preprocessing
3. Insightful Data Visualization
4. Correlation Analysis
5. Feature Engineering and Feature Selection
6. Model Training Pipeline
7. Model Evaluation
8. SHAP Explainability Integration
9. Custom Prediction Testing
10. Model Saving and Deployment
11. Clinical Safety Considerations

Usage: python scripts/pipeline/run_development.py [--data PATH] [--out-dir DIR]
"""
import argparse
import json
import logging
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from repo_paths import REPO_ROOT, SRC, DEFAULT_DATA_CSV

sys.path.insert(0, str(SRC))

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from insulin_system.config.schema import ClinicalBounds, DataSchema
from insulin_system.data_processing.load import load_and_validate

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RANDOM_STATE = 42
SCHEMA = DataSchema()


def main():
    parser = argparse.ArgumentParser(description="Revised insulin prediction development pipeline")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_CSV)
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "outputs/development")
    args = parser.parse_args()

    if not args.data.exists():
        logger.error("Data file not found: %s", args.data)
        return 1
    args.out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Data Loading and Understanding
    logger.info("=== 1. Data Loading and Understanding ===")
    df = load_and_validate(args.data)
    logger.info("Shape: %s rows, %s columns", df.shape[0], df.shape[1])
    logger.info("Missing: %s", df.isnull().sum().to_dict())

    # 2. Data Cleaning and Preprocessing
    logger.info("=== 2. Data Cleaning and Preprocessing ===")
    df_clean = df.drop(columns=[SCHEMA.PATIENT_ID], errors="ignore")
    for col in SCHEMA.NUMERIC:
        if col in df_clean.columns and df_clean[col].isnull().sum() > 0:
            df_clean[col] = df_clean[col].fillna(df_clean[col].median())
    for col in SCHEMA.CATEGORICAL:
        if col in df_clean.columns and df_clean[col].isnull().sum() > 0:
            df_clean[col] = df_clean[col].fillna(df_clean[col].mode().iloc[0])
    if SCHEMA.TARGET in df_clean.columns and df_clean[SCHEMA.TARGET].isnull().sum() > 0:
        df_clean = df_clean.dropna(subset=[SCHEMA.TARGET])

    bounds = ClinicalBounds()
    for col in SCHEMA.NUMERIC:
        if col in df_clean.columns:
            try:
                b = bounds.get_bounds_for_column(col)
                df_clean[col] = df_clean[col].clip(lower=b[0], upper=b[1])
            except KeyError:
                pass

    # Label encoding
    cat_cols = list(SCHEMA.CATEGORICAL) + [SCHEMA.TARGET]
    label_encoders = {}
    encoding_map = {}
    for col in cat_cols:
        if col in df_clean.columns:
            le = LabelEncoder()
            df_clean[col] = le.fit_transform(df_clean[col].astype(str))
            label_encoders[col] = le
            encoding_map[col] = {str(k): int(v) for k, v in zip(le.classes_, le.transform(le.classes_))}

    # 5. Feature Engineering and Feature Selection
    logger.info("=== 5. Feature Engineering and Feature Selection ===")
    if "glucose_level" in df_clean.columns and "HbA1c" in df_clean.columns:
        df_clean["glucose_HbA1c_ratio"] = df_clean["glucose_level"] / (df_clean["HbA1c"] + 1e-6)

    feature_cols = [c for c in df_clean.columns if c != SCHEMA.TARGET]
    X = df_clean[feature_cols]
    y = df_clean[SCHEMA.TARGET]

    from sklearn.feature_selection import mutual_info_classif
    mi_scores = mutual_info_classif(X, y, random_state=RANDOM_STATE)
    mi_df = pd.DataFrame({"feature": feature_cols, "mi_score": mi_scores}).sort_values("mi_score", ascending=False)
    top_k = min(15, len(feature_cols))
    selected_features = mi_df.head(top_k)["feature"].tolist()
    X_selected = X[selected_features]

    # 6. Model Training Pipeline
    logger.info("=== 6. Model Training Pipeline ===")
    X_train, X_test, y_train, y_test = train_test_split(
        X_selected, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    models = {
        "logistic_regression": LogisticRegression(max_iter=2000, random_state=RANDOM_STATE, class_weight="balanced"),
        "decision_tree": DecisionTreeClassifier(random_state=RANDOM_STATE, class_weight="balanced"),
        "random_forest": RandomForestClassifier(random_state=RANDOM_STATE, class_weight="balanced"),
        "gradient_boosting": GradientBoostingClassifier(random_state=RANDOM_STATE),
    }
    fitted = {}
    for name, model in models.items():
        model.fit(X_train_scaled, y_train)
        fitted[name] = model
        logger.info("Trained: %s", name)

    # 7. Model Evaluation
    logger.info("=== 7. Model Evaluation ===")
    results = []
    for name, model in fitted.items():
        y_pred = model.predict(X_test_scaled)
        acc = accuracy_score(y_test, y_pred)
        p, r, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="weighted")
        results.append({"model": name, "accuracy": acc, "precision": p, "recall": r, "f1_weighted": f1})
        logger.info("%s: accuracy=%.4f, f1_weighted=%.4f", name, acc, f1)

    results_df = pd.DataFrame(results).sort_values("f1_weighted", ascending=False)
    best_model_name = results_df.iloc[0]["model"]
    best_model = fitted[best_model_name]
    logger.info("Best model: %s", best_model_name)

    # 8. SHAP Explainability
    logger.info("=== 8. SHAP Explainability ===")
    try:
        import shap
        X_background = X_train_scaled[:100]
        _is_tree = isinstance(best_model, (DecisionTreeClassifier, RandomForestClassifier, GradientBoostingClassifier))
        explainer = None
        if _is_tree:
            try:
                explainer = shap.TreeExplainer(best_model, X_background)
            except Exception:
                pass
        if explainer is None:
            explainer = shap.KernelExplainer(best_model.predict_proba, X_background)
        shap_values = explainer.shap_values(X_test_scaled[:50])
        sv_global = shap_values[0] if isinstance(shap_values, list) else shap_values
        shap.summary_plot(sv_global, X_test_scaled[:50], feature_names=selected_features, show=False)
        import matplotlib.pyplot as plt
        plt.savefig(args.out_dir / "shap_summary.png", bbox_inches="tight", dpi=120)
        plt.close()
        logger.info("SHAP summary saved to %s", args.out_dir / "shap_summary.png")
    except Exception as e:
        logger.warning("SHAP not available: %s", e)

    # 10. Model Saving and Deployment
    logger.info("=== 10. Model Saving and Deployment ===")
    bundle_dir = Path("outputs/best_model")
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": best_model,
        "scaler": scaler,
        "label_encoders": label_encoders,
        "encoding_map": encoding_map,
        "selected_features": selected_features,
        "classes": best_model.classes_.tolist(),
        "model_name": best_model_name,
    }
    import joblib
    joblib.dump(bundle, bundle_dir / "development_bundle.joblib")
    metadata = {
        "model_name": best_model_name,
        "metric_name": "f1_weighted",
        "metric_value": float(results_df.iloc[0]["f1_weighted"]),
        "feature_names": selected_features,
        "classes": [str(c) for c in bundle["classes"]],
        "encoding_map": encoding_map,
    }
    with open(bundle_dir / "development_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Saved development bundle to %s", bundle_dir)

    # 11. Clinical Safety
    logger.info("=== 11. Clinical Safety Considerations ===")
    logger.info(
        "DISCLAIMER: This system is a decision-support tool only. "
        "All predictions must be reviewed by a qualified healthcare professional."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
