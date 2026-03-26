"""Generate PDF report (matplotlib PdfPages)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from smart_sensor_ml import config

logger = logging.getLogger(__name__)


def _text_page(pdf: PdfPages, title: str, lines: List[str]) -> None:
    fig = plt.figure(figsize=(8.5, 11))
    fig.text(0.08, 0.92, title, fontsize=14, fontweight="bold")
    y = 0.86
    for line in lines:
        fig.text(0.08, y, line, fontsize=10, family="monospace", wrap=True)
        y -= 0.028
        if y < 0.08:
            pdf.savefig(fig)
            plt.close(fig)
            fig = plt.figure(figsize=(8.5, 11))
            y = 0.92
    pdf.savefig(fig)
    plt.close(fig)


def build_pdf_report(
    out_pdf: Path,
    summary: Dict[str, Any],
    comparison_df: pd.DataFrame,
    best_model_name: str,
    selection_rationale: str,
    example_prediction: Dict[str, Any],
    figure_paths: List[Path],
) -> None:
    out_pdf = Path(out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(out_pdf) as pdf:
        _text_page(
            pdf,
            "Smart Sensor ML — System overview",
            [
                "End-to-end pipeline: load → validate → preprocess → train → evaluate → deploy.",
                f"Dataset: SmartSensor diabetes monitoring (15-min rows, ~100 patients).",
                "Target: Insulin_Dose (continuous units); tiers at inference are tertiles from training only.",
                "Patient-level 70/10/20 split prevents patient leakage.",
                "Cross-validation: GroupKFold on training patients (regression).",
                "",
                "Stages implemented:",
                "  1. Input layer (CSV load + EDA)",
                "  2. Validation (schema, duplicates, soft domain bounds)",
                "  3–4. Preprocessing (imputation, IQR cap, time cyclical features, correlation filter, scaling)",
                "  5. Models: Logistic Regression, Random Forest, Gradient Boosting, XGBoost/LightGBM if installed, LSTM (TensorFlow optional)",
                "  6. Metrics: R², RMSE, MAE (train/val/test)",
                "  7–8. predict_new_data() + rule-based recommend()",
                "  10. joblib bundle: model + preprocessor",
            ],
        )
        buf = ["Model comparison (hold-out test):"]
        if comparison_df is not None and not comparison_df.empty:
            buf.append(comparison_df.to_string(index=False))
        else:
            buf.append("(no table)")
        buf.extend(["", f"Selected model: {best_model_name}", "", "Justification:", selection_rationale])
        _text_page(pdf, "Model comparison & selection", buf)

        ex_lines = ["Example prediction + recommendation:", ""]
        import json

        ex_lines.append(json.dumps(example_prediction, indent=2)[:3500])
        _text_page(pdf, "Example output", ex_lines)

        for p in figure_paths:
            p = Path(p)
            if not p.is_file():
                continue
            try:
                fig = plt.figure(figsize=(8.5, 6))
                ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
                ax.axis("off")
                img = plt.imread(p)
                ax.imshow(img)
                pdf.savefig(fig)
                plt.close(fig)
            except Exception as e:
                logger.warning("Skip figure %s: %s", p, e)

    logger.info("Wrote PDF report to %s", out_pdf)
