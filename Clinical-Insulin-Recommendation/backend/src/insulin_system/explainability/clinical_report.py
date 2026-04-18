"""
Clinical explanations: translate SHAP to language, patient reports, similar patients, uncertainty.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _HAS_MPL = True
except ImportError:
    _HAS_MPL = False

from ..config.schema import ExplainabilityConfig

logger = logging.getLogger(__name__)

# Map feature names to short clinical descriptions for reports
CLINICAL_FEATURE_NAMES: Dict[str, str] = {
    "age": "Age",
    "glucose_level": "Blood glucose level (mg/dL)",
    "physical_activity": "Physical activity level",
    "BMI": "Body Mass Index",
    "HbA1c": "HbA1c (%)",
    "weight": "Body weight (kg)",
    "insulin_sensitivity": "Insulin sensitivity",
    "sleep_hours": "Sleep duration (hours)",
    "creatinine": "Serum creatinine (mg/dL)",
    "metabolic_risk_score": "Composite metabolic risk score",
    "glycemic_burden": "Glycemic burden score",
    "bmi_glucose_interaction": "BMI–glucose interaction",
    "glucose_level_insulin_sensitivity_interaction": "Glucose–insulin sensitivity interaction",
    "temporal_rank": "Temporal order (rank)",
    "temporal_segment": "Time segment",
}


@dataclass
class PatientExplanationReport:
    """Patient-specific explanation and recommendation summary."""
    patient_index: int
    predicted_class: str
    confidence: float
    uncertainty_entropy: float
    clinical_summary: str
    top_drivers: List[Dict[str, Any]]
    recommendation: str
    similar_patients: List[Dict[str, Any]]
    counterfactuals: List[Dict[str, Any]] = field(default_factory=list)


class ClinicalReportGenerator:
    """Generates clinical-language explanations and patient reports."""

    def __init__(self, config: Optional[ExplainabilityConfig] = None):
        self._cfg = config or ExplainabilityConfig()
        self._feature_names_map = self._cfg.feature_name_to_clinical or CLINICAL_FEATURE_NAMES

    def translate_shap_to_clinical(
        self,
        feature_name: str,
        shap_value: float,
        feature_value: float,
        predicted_class: str,
    ) -> str:
        """One sentence: how this feature contributed in clinical terms."""
        desc = self._feature_names_map.get(feature_name, feature_name)
        if shap_value > 0:
            return f"Higher {desc} ({feature_value:.1f}) supported the model toward '{predicted_class}'."
        return f"Lower {desc} ({feature_value:.1f}) reduced support for '{predicted_class}'."

    def confidence_and_uncertainty(self, proba: np.ndarray) -> Tuple[float, float]:
        """Return (confidence for predicted class, entropy)."""
        if proba is None or len(proba) == 0:
            return 0.0, 0.0
        idx = int(np.argmax(proba))
        confidence = float(proba[idx])
        eps = 1e-10
        entropy = float(-np.sum(proba * np.log(proba + eps)))
        return confidence, entropy

    def find_similar_patients(
        self,
        X: np.ndarray,
        query_idx: int,
        k: int,
        y: Optional[np.ndarray] = None,
    ) -> List[Dict[str, Any]]:
        """k-NN in feature space; return list of {index, distance, outcome if y provided}."""
        k = min(k, len(X) - 1)
        nn = NearestNeighbors(n_neighbors=k + 1, metric="euclidean").fit(X)
        dists, indices = nn.kneighbors(X[query_idx : query_idx + 1])
        dists = dists[0]
        indices = indices[0]
        # Drop self
        self_mask = indices != query_idx
        indices = indices[self_mask][:k]
        dists = dists[self_mask][:k]
        out = []
        for i, (idx, d) in enumerate(zip(indices, dists)):
            rec = {"index": int(idx), "distance": float(d)}
            if y is not None:
                rec["outcome"] = str(y[idx])
            out.append(rec)
        return out

    def generate_patient_report(
        self,
        patient_index: int,
        X: np.ndarray,
        y_pred: Any,
        proba: Optional[np.ndarray],
        shap_values_one: np.ndarray,
        feature_names: List[str],
        classes: np.ndarray,
        y_true: Optional[np.ndarray] = None,
        counterfactuals: Optional[List[Dict[str, Any]]] = None,
    ) -> PatientExplanationReport:
        """Build a single patient explanation report."""
        pred_class = str(y_pred) if not isinstance(y_pred, (int, np.integer)) else str(classes[int(y_pred)])
        confidence = 0.0
        entropy = 0.0
        if proba is not None:
            confidence, entropy = self.confidence_and_uncertainty(proba)
        x = X[patient_index]
        order = np.argsort(np.abs(shap_values_one))[::-1][: self._cfg.top_k_features]
        top_drivers = []
        for i in order:
            fname = feature_names[i] if i < len(feature_names) else f"feature_{i}"
            top_drivers.append({
                "feature": fname,
                "clinical_name": self._feature_names_map.get(fname, fname),
                "value": float(x[i]),
                "shap_value": float(shap_values_one[i]),
                "sentence": self.translate_shap_to_clinical(fname, float(shap_values_one[i]), float(x[i]), pred_class),
            })
        clinical_summary = " ".join(d["sentence"] for d in top_drivers[:3])
        similar = self.find_similar_patients(X, patient_index, self._cfg.similar_patients_k, y_true)
        recommendation = (
            f"Model predicts insulin dosage category '{pred_class}' (confidence {confidence:.0%}). "
            "Review top drivers above. Consider similar patients' outcomes for context."
        )
        return PatientExplanationReport(
            patient_index=patient_index,
            predicted_class=pred_class,
            confidence=confidence,
            uncertainty_entropy=entropy,
            clinical_summary=clinical_summary,
            top_drivers=top_drivers,
            recommendation=recommendation,
            similar_patients=similar,
            counterfactuals=counterfactuals or [],
        )

    def write_report_to_file(self, report: PatientExplanationReport, path: Path) -> None:
        """Write a text summary of the report to a file."""
        lines = [
            f"# Patient Explanation Report (index {report.patient_index})",
            f"Predicted class: {report.predicted_class}",
            f"Confidence: {report.confidence:.0%}",
            f"Uncertainty (entropy): {report.uncertainty_entropy:.3f}",
            "",
            "## Top contributing factors",
        ]
        for d in report.top_drivers:
            lines.append(f"- {d['sentence']}")
        lines.extend(["", "## Recommendation", report.recommendation, "", "## Similar patients"])
        for s in report.similar_patients:
            lines.append(f"- Index {s['index']}, distance {s['distance']:.3f}" + (f", outcome {s.get('outcome', '')}" if "outcome" in s else ""))
        if report.counterfactuals:
            lines.extend(["", "## Counterfactual notes"])
            for c in report.counterfactuals:
                lines.append(f"- {c.get('suggestion', c)}")
        path.write_text("\n".join(lines), encoding="utf-8")

    def plot_similar_patients_comparison(
        self,
        X: np.ndarray,
        query_idx: int,
        similar_indices: List[int],
        feature_names: List[str],
        top_k_features: int = 8,
        save_path: Optional[Path] = None,
    ) -> None:
        """Create comparison visualization: current patient vs similar patients (mean) on top features."""
        if not _HAS_MPL or not similar_indices:
            return
        n_show = min(top_k_features, X.shape[1], len(feature_names))
        if n_show == 0:
            return
        x_query = X[query_idx]
        x_similar = X[similar_indices]
        mean_similar = np.mean(x_similar, axis=0)
        # Use first n_show features or by variance for interest
        var = np.var(x_similar, axis=0)
        order = np.argsort(var)[::-1][:n_show]
        labels = [feature_names[i] if i < len(feature_names) else f"F{i}" for i in order]
        q_vals = [float(x_query[i]) for i in order]
        s_vals = [float(mean_similar[i]) for i in order]
        x_pos = np.arange(len(labels))
        width = 0.35
        fig, ax = plt.subplots(figsize=(max(8, len(labels) * 0.8), 5))
        ax.bar(x_pos - width / 2, q_vals, width, label="This patient", color="steelblue", alpha=0.9)
        ax.bar(x_pos + width / 2, s_vals, width, label="Similar patients (mean)", color="coral", alpha=0.9)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_ylabel("Feature value")
        ax.set_title("Comparison: This patient vs similar patients")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()
