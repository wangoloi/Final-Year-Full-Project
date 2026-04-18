"""
SHAP-based Explainability Module (Step 5).

Global: feature importance, dependence plots, interactions, cohort analysis.
Local: force plots, waterfall, tree explanations, counterfactuals.
Clinical: language translation, patient reports, similar patients, uncertainty.
"""

from .shap_explainer import SHAPExplainer, ExplainerResult
from .clinical_report import ClinicalReportGenerator, PatientExplanationReport

__all__ = [
    "SHAPExplainer",
    "ExplainerResult",
    "ClinicalReportGenerator",
    "PatientExplanationReport",
]
