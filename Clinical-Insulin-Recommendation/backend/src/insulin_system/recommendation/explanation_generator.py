"""
Explanation generator: natural language explanations, key factors, what-if analysis, similar patients.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from ..config.schema import RecommendationConfig
from .recommendation_generator import ClinicalRecommendation

logger = logging.getLogger(__name__)


@dataclass
class ExplanationOutput:
    """Natural language and structured explanation for a recommendation."""

    natural_language_summary: str
    key_contributing_factors: List[Dict[str, Any]] = field(default_factory=list)
    alternative_scenarios: List[str] = field(default_factory=list)
    similar_patients_summary: Optional[str] = None
    similar_patients: List[Dict[str, Any]] = field(default_factory=list)


class RecommendationExplanationGenerator:
    """
    Creates natural language explanations for recommendations.
    Can optionally use SHAP explainer and reference cohort for key factors and similar patients.
    """

    def __init__(
        self,
        config: Optional[RecommendationConfig] = None,
        shap_explainer: Optional[Any] = None,
        reference_X: Optional[np.ndarray] = None,
        reference_y: Optional[np.ndarray] = None,
        feature_names: Optional[List[str]] = None,
    ) -> None:
        self._cfg = config or RecommendationConfig()
        self._shap = shap_explainer
        self._X_ref = reference_X
        self._y_ref = reference_y
        self._feature_names = feature_names or []

    def generate(
        self,
        clinical_recommendation: ClinicalRecommendation,
        patient_features: Optional[np.ndarray] = None,
        predicted_class: Optional[str] = None,
        proba: Optional[np.ndarray] = None,
        query_index_in_ref: Optional[int] = None,
        counterfactuals: Optional[List[Dict[str, Any]]] = None,
    ) -> ExplanationOutput:
        """
        Build full explanation: NL summary, key factors, what-if scenarios, similar patients.
        patient_features: transformed feature vector (for similar-patient search when no query_index_in_ref).
        query_index_in_ref: index into reference set for similar-patient search; else use patient_features.
        counterfactuals: optional list of dicts with 'suggestion' (e.g. from SHAPExplainer.counterfactual).
        """
        rec = clinical_recommendation
        pred = predicted_class or rec.predicted_class
        dosage = rec.dosage_suggestion

        # Natural language summary
        nl_parts = [
            f"The model predicts insulin category **{pred}** with {rec.confidence:.0%} confidence.",
            dosage.summary,
            dosage.detail,
        ]
        if rec.is_high_risk and rec.high_risk_reason:
            nl_parts.append(f" **Flag for clinician review:** {rec.high_risk_reason}")
        natural_language_summary = " ".join(nl_parts)

        # Key contributing factors (from probability breakdown or placeholder)
        key_factors: List[Dict[str, Any]] = []
        if rec.probability_breakdown:
            for cls_name, p in sorted(rec.probability_breakdown.items(), key=lambda x: -x[1])[: self._cfg.top_k_features]:
                key_factors.append({"class": cls_name, "probability": float(p), "description": f"P({cls_name}) = {p:.0%}"})
        if not key_factors and proba is not None and len(proba) > 0:
            for i in np.argsort(proba)[::-1][: self._cfg.top_k_features]:
                key_factors.append({"index": int(i), "probability": float(proba[i]), "description": f"Class index {i}: {proba[i]:.0%}"})

        # Alternative scenarios (what-if): use provided counterfactuals or defaults
        alternative_scenarios: List[str] = []
        if counterfactuals:
            for c in counterfactuals[:5]:
                alternative_scenarios.append(c.get("suggestion", str(c)))
        if not alternative_scenarios:
            alternative_scenarios = [
                "If glucose or HbA1c were lower, the model might suggest maintaining or reducing dosage.",
                "If glucose or HbA1c were higher, the model might suggest increasing dosage.",
            ]

        # Similar patients
        similar_patients: List[Dict[str, Any]] = []
        similar_summary: Optional[str] = None
        if self._X_ref is not None and (query_index_in_ref is not None or patient_features is not None):
            try:
                from sklearn.neighbors import NearestNeighbors

                k = self._cfg.similar_patients_k
                if query_index_in_ref is not None:
                    xq = self._X_ref[query_index_in_ref : query_index_in_ref + 1]
                    nn = NearestNeighbors(
                        n_neighbors=min(k + 1, len(self._X_ref)), metric="euclidean"
                    ).fit(self._X_ref)
                    dists, indices = nn.kneighbors(xq)
                    indices = indices[0]
                    dists = dists[0]
                    for idx, d in zip(indices[: k + 1], dists[: k + 1]):
                        if int(idx) == query_index_in_ref:
                            continue
                        rec_dict = {"index": int(idx), "distance": float(d)}
                        if self._y_ref is not None:
                            rec_dict["outcome"] = str(self._y_ref[idx])
                        similar_patients.append(rec_dict)
                        if len(similar_patients) >= k:
                            break
                else:
                    nn = NearestNeighbors(n_neighbors=min(k + 1, len(self._X_ref)), metric="euclidean").fit(
                        self._X_ref
                    )
                    dists, indices = nn.kneighbors(patient_features.reshape(1, -1))
                    indices = indices[0]
                    dists = dists[0]
                    for idx, d in zip(indices[:k], dists[:k]):
                        rec_dict = {"index": int(idx), "distance": float(d)}
                        if self._y_ref is not None:
                            rec_dict["outcome"] = str(self._y_ref[idx])
                        similar_patients.append(rec_dict)
                if self._y_ref is not None and similar_patients:
                    outcomes = [s.get("outcome", "?") for s in similar_patients]
                    similar_summary = f"Among {k} similar patients, outcomes: {', '.join(outcomes)}."
            except Exception as e:
                logger.debug("Similar patients lookup failed: %s", e)

        return ExplanationOutput(
            natural_language_summary=natural_language_summary,
            key_contributing_factors=key_factors,
            alternative_scenarios=alternative_scenarios,
            similar_patients_summary=similar_summary,
            similar_patients=similar_patients,
        )
