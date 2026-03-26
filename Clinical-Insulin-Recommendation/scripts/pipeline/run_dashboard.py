"""
GlucoSense Clinical Support - Visualization Dashboard (Step 7).

Run: streamlit run scripts/pipeline/run_dashboard.py

Type 1 Diabetes Management: patient-level and population-level insights,
clinical tools, and treatment pathway support.
"""
from __future__ import annotations

import sys
from pathlib import Path

from repo_paths import REPO_ROOT, SRC, DEFAULT_DATA_CSV

sys.path.insert(0, str(SRC))

import streamlit as st
import pandas as pd
import numpy as np

from insulin_system.config.schema import DashboardConfig, DataSchema
from insulin_system.dashboard.data_loader import load_dashboard_data

# Page config
st.set_page_config(
    page_title="GlucoSense Clinical Support",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar: section and data path
st.sidebar.title("GlucoSense Clinical Support")
st.sidebar.markdown("Type 1 Diabetes Management")
section = st.sidebar.radio(
    "Dashboard",
    ["Patient-Level", "Population-Level", "Clinical Tools"],
    index=0,
)
_default_data_rel = str(DEFAULT_DATA_CSV.relative_to(REPO_ROOT)).replace("\\", "/")
data_path = st.sidebar.text_input(
    "Data path (for reference & profiles)",
    value=_default_data_rel,
)
cfg = DashboardConfig(data_path=Path(data_path) if data_path else DEFAULT_DATA_CSV)

# Load data (cached)
@st.cache_data(ttl=300)
def get_data():
    return load_dashboard_data(cfg, cfg.data_path, run_pipeline_for_reference=True)

data = get_data()

# Main branding
st.markdown("# GlucoSense Clinical Support")
st.markdown("**Type 1 Diabetes Management**")
st.markdown("---")

# --- Patient-Level Dashboard ---
if section == "Patient-Level":
    st.header("Patient-Level Dashboard")
    if not data.bundle:
        st.warning("No saved model found. Run evaluation first: `python scripts/pipeline/run_evaluation.py`")
        st.stop()

    n_ref = len(data.reference_X) if data.reference_X is not None else 0
    patient_options = list(range(min(100, n_ref))) if n_ref else []
    if not patient_options:
        st.info("Set a valid data path in the sidebar and reload to load reference patients.")
        patient_options = [0]
    patient_idx = st.selectbox(
        "Select patient index",
        patient_options,
        format_func=lambda i: f"Patient {i}" + (f" (of {n_ref})" if n_ref else ""),
    )

    if data.reference_df is not None and data.reference_X is not None and n_ref and patient_idx < len(data.reference_df):
        raw_row = data.reference_df.iloc[patient_idx]
        X_one = data.reference_X[patient_idx : patient_idx + 1]
        pred = data.bundle.predict(X_one)[0]
        proba = data.bundle.predict_proba(X_one)[0]
        conf = float(proba[list(data.classes).index(pred)])
        entropy = float(-(proba * np.log(proba + 1e-10)).sum())

        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("Profile summary")
            profile_cols = [c for c in raw_row.index if c not in (DataSchema().TARGET, "_outlier_flag")]
            profile = raw_row[profile_cols].astype(str)
            st.dataframe(profile.to_frame("Value"), use_container_width=True, hide_index=True)
        with col2:
            st.subheader("Prediction")
            st.metric("Predicted category", str(pred))
            st.metric("Confidence", f"{conf:.0%}")
            st.metric("Uncertainty (entropy)", f"{entropy:.3f}")
        with col3:
            st.subheader("Probability breakdown")
            for c, p in zip(data.classes, proba):
                st.progress(float(p), text=f"{c}: {p:.0%}")

        st.subheader("SHAP-based explanation")
        model_name = data.model_name or "random_forest"
        expl_dir = cfg.explainability_dir / model_name
        # Show waterfall/force for this index if available
        found = False
        for key, path in data.explainability_paths.items():
            if f"waterfall_{patient_idx}" in key or f"force_{patient_idx}" in key:
                if path.endswith(".html"):
                    with open(path, encoding="utf-8") as f:
                        st.components.v1.html(f.read(), height=400, scrolling=True)
                    found = True
                    break
        if not found and (expl_dir / "shap_summary.png").exists():
            st.image(str(expl_dir / "shap_summary.png"), caption="Global SHAP summary")
        if not found and not (expl_dir / "shap_summary.png").exists():
            st.info("Run explainability for this model to see SHAP plots: `python run_explainability.py`")

        st.subheader("Recommendation with reasoning")
        rec_list = [r for r in data.recommendations if r.get("patient_index") == patient_idx]
        if rec_list:
            r = rec_list[0]
            st.markdown(r.get("natural_language", ""))
            st.markdown("**Alternative scenarios**")
            for s in r.get("alternative_scenarios", []):
                st.markdown(f"- {s}")
            if r.get("similar_patients_summary"):
                st.markdown(r["similar_patients_summary"])
        else:
            from insulin_system.recommendation import RecommendationGenerator
            rec_gen = RecommendationGenerator()
            prob_breakdown = {str(c): float(proba[i]) for i, c in enumerate(data.classes)}
            rec = rec_gen.generate(str(pred), conf, entropy, prob_breakdown)
            st.markdown(rec.dosage_suggestion.summary)
            st.markdown(rec.dosage_suggestion.detail)
            if rec.is_high_risk and rec.high_risk_reason:
                st.warning(f"Flag for review: {rec.high_risk_reason}")
    else:
        st.info("Set a valid data path in the sidebar to load reference patients and see profile, prediction, and recommendation.")

# --- Population-Level Dashboard ---
elif section == "Population-Level":
    st.header("Population-Level Dashboard")

    if data.evaluation_summary is not None:
        st.subheader("Model performance summary")
        st.dataframe(data.evaluation_summary.style.highlight_max(subset=["f1_weighted", "accuracy"], axis=0), use_container_width=True)

    if data.reference_y is not None and len(data.reference_y) > 0:
        st.subheader("Insulin dosage distribution (reference test set)")
        dist = pd.Series(data.reference_y).value_counts().sort_index()
        import plotly.express as px
        fig = px.bar(x=dist.index.astype(str), y=dist.values, labels={"x": "Category", "y": "Count"}, title="Distribution of insulin category")
        st.plotly_chart(fig, use_container_width=True)

    if data.evaluation_summary is not None and not data.evaluation_summary.empty:
        st.subheader("Feature importance & performance trends")
        best_model = data.evaluation_summary.iloc[0]["model"]
        art_dir = cfg.evaluation_dir / best_model
        imp_path = art_dir / "feature_importance_permutation.png"
        if imp_path.exists():
            st.image(str(imp_path), caption="Permutation feature importance")
        imp_builtin = art_dir / "feature_importance_builtin.png"
        if imp_builtin.exists():
            st.image(str(imp_builtin), caption="Built-in feature importance")

    if data.temporal_validation is not None and not data.temporal_validation.empty:
        st.subheader("Model performance over time (temporal segments)")
        import plotly.express as px
        fig = px.line(
            data.temporal_validation,
            x="temporal_segment",
            y=["accuracy", "f1_weighted"],
            title="Metrics by time segment",
        )
        st.plotly_chart(fig, use_container_width=True)

    if data.reference_y is not None and data.reference_X is not None and len(data.reference_y) > 0:
        st.subheader("Cohort comparison (by predicted category)")
        preds = data.bundle.predict(data.reference_X)
        cohort = pd.DataFrame({"actual": data.reference_y, "predicted": preds})
        ctab = pd.crosstab(cohort["actual"], cohort["predicted"])
        st.dataframe(ctab, use_container_width=True)
        fig = px.imshow(ctab, labels=dict(x="Predicted", y="Actual", color="Count"), text_auto=True)
        st.plotly_chart(fig, use_container_width=True)

# --- Clinical Tools ---
else:
    st.header("Clinical Tools")

    if not data.bundle:
        st.warning("Load a model first (run evaluation).")
        st.stop()

    st.subheader("Similar patient search and comparison")
    k = st.slider("Number of similar patients", 3, 15, 5)
    if data.reference_X is not None and data.reference_y is not None:
        query_idx = st.number_input("Reference patient index", min_value=0, max_value=max(0, len(data.reference_X) - 1), value=0)
        if st.button("Find similar patients"):
            from sklearn.neighbors import NearestNeighbors
            nn = NearestNeighbors(n_neighbors=min(k + 1, len(data.reference_X)), metric="euclidean").fit(data.reference_X)
            dists, indices = nn.kneighbors(data.reference_X[query_idx : query_idx + 1])
            indices = indices[0][1 : k + 1]
            dists = dists[0][1 : k + 1]
            similar = pd.DataFrame({
                "index": indices,
                "distance": dists,
                "outcome": [str(data.reference_y[i]) for i in indices],
            })
            st.dataframe(similar, use_container_width=True)
            st.caption("Outcomes of similar patients in the reference set.")

    st.subheader("Treatment outcome analysis")
    if data.reference_y is not None and data.reference_X is not None:
        preds = data.bundle.predict(data.reference_X)
        acc = np.mean(np.array(preds) == np.array(data.reference_y))
        st.metric("Accuracy on reference set", f"{acc:.1%}")
        from sklearn.metrics import classification_report
        st.text(classification_report(data.reference_y, preds, target_names=list(data.classes), zero_division=0))

    st.subheader("Adverse event risk indicators")
    st.markdown("Predictions with **low confidence** or **high uncertainty** are flagged for clinician review.")
    if data.recommendations:
        high_risk = [r for r in data.recommendations if r.get("is_high_risk")]
        st.metric("High-risk flagged (from last run)", len(high_risk))
        if high_risk:
            st.dataframe(pd.DataFrame(high_risk)[["patient_index", "predicted_class", "confidence", "recommendation_summary"]], use_container_width=True)
    else:
        st.info("Run the recommendation script to populate risk flags: `python run_recommendation.py --data ...`")

    st.subheader("Treatment pathway")
    st.markdown("""
    1. **Input** → Patient features (glucose, HbA1c, BMI, etc.)  
    2. **Model** → Predicted insulin category (down / up / steady / no)  
    3. **Recommendation** → Dosage suggestion + confidence  
    4. **Review** → High-risk cases flagged for clinician  
    5. **Action** → Adjust dosage per clinical guidelines  
    """)
    if data.model_name:
        st.caption(f"Current model: {data.model_name}")

st.sidebar.markdown("---")
st.sidebar.caption("GlucoSense Clinical Support v0.1")
