"""
Clinician-style narrative for RecommendationResponse: model drivers, uncertainty factors, synthesis.

Grounded in transparent CDS practice (clear inputs, limits of certainty, person-first language).
See ADA Standards of Care on person-first communication; IPDAS-style option clarity for decision support.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from clinical_insulin_pipeline.models import get_feature_importance_vector

from ..validators import NUMERIC_KEYS

# Human-readable labels for model features (aligned with bundle feature_names).
FEATURE_LABELS: Dict[str, str] = {
    "age": "Age",
    "glucose_level": "Blood glucose",
    "physical_activity": "Physical activity",
    "BMI": "BMI",
    "HbA1c": "HbA1c",
    "weight": "Weight",
    "insulin_sensitivity": "Insulin sensitivity",
    "sleep_hours": "Sleep duration",
    "creatinine": "Creatinine",
    "gender": "Sex",
    "family_history": "Family history",
    "food_intake": "Food intake",
    "previous_medications": "Prior medications",
    "iob": "Insulin on board",
    "anticipated_carbs": "Anticipated carbohydrates",
    "glucose_trend_encoded": "Glucose trend",
}


def humanize_feature_name(name: str) -> str:
    return FEATURE_LABELS.get(name, name.replace("_", " ").title())


def top_feature_drivers(bundle_data: Dict[str, Any], feature_names: List[str], k: int = 3) -> List[Dict[str, Any]]:
    """
    Top-k features by global model importance (forest / linear coef magnitude when available).
    """
    model = bundle_data.get("model")
    if model is None or not feature_names:
        return []
    imp = get_feature_importance_vector(model, len(feature_names))
    if imp is None or len(imp) != len(feature_names):
        return []
    imp = np.asarray(imp, dtype=float)
    idx = np.argsort(imp)[::-1][:k]
    total = float(np.sum(imp)) or 1.0
    out: List[Dict[str, Any]] = []
    for rank, i in enumerate(idx, start=1):
        fn = feature_names[int(i)]
        out.append(
            {
                "feature": fn,
                "label": humanize_feature_name(fn),
                "importance": float(imp[i]),
                "importance_relative": float(imp[i] / total),
                "rank": rank,
            }
        )
    return out


def _format_patient_value_for_feature(feature: str, patient_dict: Dict[str, Any]) -> Optional[str]:
    """One-line value context for transparency (no diagnostic claims)."""
    v = patient_dict.get(feature)
    if v is None:
        return None
    try:
        if feature == "glucose_level":
            return f"{float(v):.0f} mg/dL"
        if feature in ("HbA1c", "BMI"):
            return f"{float(v):.1f}"
        if feature == "weight":
            return f"{float(v):.1f} kg"
        if feature == "iob":
            return f"{float(v) * 100:.1f} units on board (from recorded IOB)"
        if feature == "anticipated_carbs":
            return f"{float(v):.0f} g carbs planned"
        if feature == "physical_activity":
            return f"activity score {float(v):.1f}"
        if feature == "age":
            return f"{float(v):.0f} years"
        if feature == "sleep_hours":
            return f"{float(v):.1f} h sleep"
        if feature == "insulin_sensitivity":
            return f"{float(v):.2f}"
        if feature == "creatinine":
            return f"{float(v):.2f} mg/dL"
    except (TypeError, ValueError):
        return None
    return str(v)[:80]


def build_contributing_factors(
    drivers: List[Dict[str, Any]],
    patient_dict: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Structured factors the recommendation used: model importance + current values when available.
    """
    out: List[Dict[str, Any]] = []
    for d in drivers:
        fn = d["feature"]
        val = _format_patient_value_for_feature(fn, patient_dict)
        note = (
            f"Current {d['label'].lower()} in your record: {val}."
            if val
            else f"{d['label']} contributes to the model estimate (value not provided or not mapped)."
        )
        out.append(
            {
                "feature": fn,
                "label": d["label"],
                "importance_rank": d["rank"],
                "relative_importance": round(d["importance_relative"], 4),
                "clinical_note": note,
            }
        )
    return out


def _tier_margin_and_runner_up(tier_probs: Optional[Dict[str, float]]) -> Tuple[float, Optional[str]]:
    """Return (margin between top two tiers, name of runner-up tier)."""
    if not tier_probs:
        return 1.0, None
    vals = [(k, float(tier_probs.get(k, 0.0))) for k in ("Low", "Moderate", "High")]
    vals.sort(key=lambda x: -x[1])
    if len(vals) < 2:
        return 1.0, None
    margin = vals[0][1] - vals[1][1]
    return margin, vals[1][0]


def tier_probs_ambiguous(tier_probs: Optional[Dict[str, float]], margin: float = 0.14) -> bool:
    """True when two dose tiers have similar model-assigned probability mass."""
    m, _ = _tier_margin_and_runner_up(tier_probs)
    return m < margin


def collect_uncertainty_factors(
    confidence: float,
    entropy: float,
    patient_dict: Dict[str, Any],
    tier_probs: Optional[Dict[str, float]],
    *,
    confidence_threshold: float = 0.75,
    entropy_threshold: float = 1.0,
    tier_ambiguity_margin: float = 0.14,
) -> List[str]:
    """
    Plain-language reasons uncertainty is elevated (for shared decision-making transparency).
    """
    factors: List[str] = []
    n_numeric = sum(1 for k in NUMERIC_KEYS if patient_dict.get(k) is not None)
    if n_numeric < 3:
        factors.append(
            "Fewer numeric details were provided than ideal; the estimate may be less individualized."
        )
    if patient_dict.get("glucose_level") is None:
        factors.append("No finger-stick or CGM glucose value was entered; glycemic context is incomplete.")
    if patient_dict.get("cgm_sensor_error") is True:
        factors.append("CGM sensor error was reported; confirm glucose with a finger-stick before acting.")
    kt = (patient_dict.get("ketone_level") or "").strip().lower()
    if kt in ("moderate", "large", "high"):
        factors.append("Elevated ketones add clinical uncertainty; in-person guidance may be needed.")
    margin, runner_up = _tier_margin_and_runner_up(tier_probs)
    if tier_probs and margin < tier_ambiguity_margin and runner_up:
        factors.append(
            f"The model places similar weight on {runner_up} and the leading dose tier; review both scenarios."
        )
    try:
        c = float(confidence)
        if c < confidence_threshold:
            factors.append(
                f"Overall model certainty is moderate ({c:.0%}); use clinical judgment alongside this suggestion."
            )
    except (TypeError, ValueError):
        pass
    try:
        e = float(entropy)
        if e > entropy_threshold:
            factors.append("Several dose tiers remain plausible given the spread of class probabilities.")
    except (TypeError, ValueError):
        pass
    return factors


def build_clinical_assessment_synthesis(
    tier: str,
    dosage_summary: str,
    dosage_detail: str,
    contributing_factors: List[Dict[str, Any]],
    uncertainty_factors: List[str],
    zone_interpretation: Optional[str],
) -> str:
    """
    Short clinician-style paragraph: assessment + basis + caveat (not a substitute for HCP).
    """
    parts: List[str] = []
    z = (zone_interpretation or "").strip()
    if z:
        parts.append(f"Glycemic context: {z}.")
    parts.append(
        f"Dose category from the model: {tier} — {dosage_summary.strip()}"
    )
    if contributing_factors:
        top = contributing_factors[0]
        lab = top.get("label", "key inputs")
        parts.append(
            f"The statistical model weights {lab} most strongly among the recorded variables."
        )
    if uncertainty_factors:
        parts.append(
            "Limitations: " + " ".join(uncertainty_factors[:2])
        )
    parts.append(
        "This is decision support only; the treating clinician should confirm dosing against your care plan."
    )
    base = " ".join(parts)
    if len(base) < 120 and dosage_detail:
        base = f"{base} {dosage_detail[:200].strip()}"
    return base.strip()


def drivers_preamble_sentence(top_feature_names: List[str], max_features: int = 2) -> str:
    """One sentence for recommendation detail: which inputs dominate (non-causal wording)."""
    if not top_feature_names:
        return ""
    names = [humanize_feature_name(n) for n in top_feature_names[:max_features]]
    if len(names) == 1:
        return f" The model’s global fit places the greatest weight on {names[0]} among recorded features."
    return f" The model’s global fit places the greatest weight on {names[0]} and {names[1]} among recorded features."
