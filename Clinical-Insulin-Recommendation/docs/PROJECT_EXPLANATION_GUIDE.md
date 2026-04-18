# Glucosense Project Explanation Guide

A comprehensive guide to understanding, explaining, and presenting the Glucosense clinical decision support system to different audiences.

---

## STEP 1 — System Understanding

### The Problem the System Solves

Type 1 diabetes requires constant insulin dosing decisions based on glucose levels, diet, activity, and other factors. Clinicians and patients need support that combines **machine learning predictions** with **clinical context** and **safety checks**—without replacing human judgment.

### Target Users

- **Primary:** Clinicians and healthcare staff managing Type 1 diabetes patients
- **Secondary:** Researchers evaluating ML-assisted dosing support

### Main Objectives

1. **Predict** insulin adjustment direction (down / up / steady / no)
2. **Recommend** dosage suggestions with magnitude, confidence, and high-risk flagging
3. **Explain** predictions using SHAP-based drivers and counterfactual scenarios
4. **Support** clinical decision-making while maintaining safety and auditability

### Key Features

| Feature | Description |
|---------|-------------|
| Prediction | ML model classifies insulin change from patient features |
| Recommendation | Clinical dosage suggestions with IOB stacking checks, glucose zones |
| Explainability | SHAP drivers, counterfactual scenarios, probability breakdown |
| Alerts | Hypoglycemia, hyperglycemia, high-risk recommendation flags |
| Audit | Every prediction logged to JSONL; records stored in SQLite |
| Dashboard | React UI for patient input, recommendations, trends, model info |

### Technologies Used

| Layer | Technologies |
|-------|--------------|
| **Backend** | Python 3.9+, FastAPI, Uvicorn, Pydantic |
| **ML** | scikit-learn, XGBoost, imbalanced-learn |
| **Explainability** | SHAP |
| **Persistence** | joblib (model bundle), SQLite |
| **Frontend** | React 18, Vite 5, React Router, Recharts, jsPDF |
| **Data** | pandas, numpy |

**Models evaluated:** Logistic Regression, Decision Tree, Random Forest, Gradient Boosting (XGBoost), SVM (RBF), MLP, RNN/LSTM.  
**Current best model:** Gradient Boosting (~60% F1-weighted).

### Overall Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React + Vite)                            │
│  Dashboard │ Reports │ Insulin Management │ Alerts │ Model Info │ Trends    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         API (FastAPI on port 8000)                           │
│  POST /predict, /explain, /recommend │ GET /model-info, /records, /alerts    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ENGINE                                          │
│  InferenceBundle (transform + predict) → RecommendationGenerator → Response │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │ SQLite DB    │  │ Audit JSONL  │  │ Best Model   │
            │ (records,    │  │ (predictions)│  │ (joblib)     │
            │  alerts)     │  │              │  │              │
            └──────────────┘  └──────────────┘  └──────────────┘
```

---

### Three Levels of Explanation

#### 1. One-Sentence Explanation

**Glucosense is a clinical decision support system that uses machine learning to predict insulin dosage adjustments for Type 1 diabetes, then translates those predictions into actionable recommendations with safety checks and explanations for clinicians.**

#### 2. 30-Second Explanation

Glucosense helps clinicians manage Type 1 diabetes by combining an ML model with clinical rules. You enter patient data—glucose, age, HbA1c, activity, and more—and the system predicts whether to increase, decrease, or maintain insulin. It then turns that prediction into a concrete recommendation (e.g., "Inject 2 units") while checking for risks like hypoglycemia or insulin stacking. Every suggestion is explained and flagged when the system is uncertain. All recommendations require clinician review—it’s a support tool, not an autonomous system.

#### 3. 2-Minute Explanation

Glucosense is a clinical decision support system for Type 1 diabetes. Clinicians enter patient data—blood glucose, HbA1c, BMI, age, food intake, physical activity, and optional fields like insulin on board (IOB) and anticipated carbs. A trained Gradient Boosting model predicts one of four outcomes: **down** (reduce dose), **up** (increase dose), **steady** (maintain), or **no** (no change needed).

The system doesn’t stop at the prediction. A **RecommendationGenerator** applies clinical rules: if glucose is below 70 mg/dL, it suspends insulin logic and recommends 15g fast-acting carbs. If blood sugar is high but there’s significant IOB and a downward trend, it withholds or reduces correction to avoid insulin stacking. It also adjusts for high physical activity and low-normal glucose.

Each recommendation includes confidence, a high-risk flag when the model is uncertain, and **SHAP-based explanations** showing which factors drove the prediction. All predictions are logged for audit, and the UI shows trends, alerts, and model performance. The system is designed to assist clinicians, not replace them—every recommendation must be reviewed by a qualified healthcare professional.

---

## STEP 2 — System Architecture Breakdown

### Sequential Workflow: From User Interaction to Output

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. USER INTERACTION (Frontend)                                                   │
│    Clinician enters patient data on Dashboard: glucose_level, age, gender,       │
│    food_intake, physical_activity, BMI, HbA1c, optional: iob, anticipated_carbs │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 2. API REQUEST                                                                   │
│    POST /api/recommend with JSON body                                            │
│    Routes receive request → validate via Pydantic (PatientInput schema)          │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 3. VALIDATION                                                                    │
│    - Age 0–100, gender Male/Female, food_intake Low/Medium/High                   │
│    - previous_medications None/Insulin/Oral (Oral requires medication_name)     │
│    - Numeric bounds (glucose 20–600, BMI 12–70, etc.)                            │
│    - Invalid → 422 with structured errors                                        │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 4. ENGINE: LOAD BUNDLE                                                           │
│    get_bundle() loads InferenceBundle from outputs/best_model/inference_bundle   │
│    .joblib (lazy load, cached)                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 5. TRANSFORM (Preprocessing)                                                      │
│    patient_input_to_dataframe() → bundle.transform(df)                            │
│    Impute → Outlier handling → Feature engineering → Encode → Scale → Select    │
│    Same pipeline as training; outputs feature matrix X                            │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 6. MODEL PREDICTION                                                              │
│    bundle.predict(X) → predicted_class (down/up/steady/no)                        │
│    bundle.predict_proba(X) → probability_breakdown, confidence, entropy           │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 7. RECOMMENDATION GENERATOR                                                      │
│    RecommendationGenerator.generate(predicted_class, confidence, entropy,        │
│    patient_dict)                                                                  │
│    - Glucose zone override (hypo → stop insulin, 15g carbs)                      │
│    - IOB stacking check (high BG + trend down + IOB → withhold/reduce)           │
│    - High glucose + no IOB + reduce → override to maintain                       │
│    - Activity adjustment (high activity → reduce dose)                           │
│    - is_high_risk if confidence < 0.75 or entropy > 1.0                           │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 8. EXPLAINABILITY (if background data available)                                 │
│    SHAPExplainer.get_top_drivers(), counterfactual()                              │
│    → explanation_drivers, alternative_scenarios                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 9. SIDE EFFECTS (parallel)                                                       │
│    - log_prediction() → outputs/audit/predictions.jsonl                           │
│    - insert_record() → SQLite glucosense.db                                       │
│    - insert_glucose_reading() for trend chart                                     │
│    - _check_critical_alerts() → insert_alert() for hypo/hyper/high-risk          │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 10. API RESPONSE                                                                 │
│     RecommendationResponse: predicted_class, confidence, dosage_action,           │
│     dose_change_units, system_interpretation, recommended_action,                 │
│     explanation_drivers, alternative_scenarios, is_high_risk, clinical disclaimer│
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 11. FRONTEND DISPLAY                                                             │
│     Dashboard shows recommendation, confidence, high-risk banner,                 │
│     explanation drivers, alternative scenarios, clinical disclaimer               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## STEP 3 — Component Explanation

### 1. **API Layer** (`app.py`, `src/insulin_system/api/`)

**What it does:** Exposes REST endpoints for prediction, explanation, recommendation, model info, records, alerts, glucose trends, and settings.

**Why it exists:** Provides a single integration point for the frontend and external systems. Handles CORS, validation, error responses, and optional static frontend serving.

**Connections:** Receives requests from frontend → delegates to engine → returns structured JSON. Writes to storage and audit in parallel.

**Technologies:** FastAPI, Pydantic, Uvicorn.

---

### 2. **Engine** (`api/engine.py`)

**What it does:** Loads the InferenceBundle once, runs `transform` + `predict` + `predict_proba`, invokes RecommendationGenerator, and optionally SHAP explainer. Returns PredictionResponse, ExplainResponse, or RecommendationResponse.

**Why it exists:** Centralizes inference logic so routes stay thin. Ensures preprocessing matches training and bundles prediction + recommendation + explanation in one place.

**Connections:** Uses InferenceBundle (persistence), RecommendationGenerator (recommendation), SHAPExplainer (explainability), config (glucose zones, display helpers).

**Technologies:** numpy, pandas, joblib.

---

### 3. **InferenceBundle** (`persistence/bundle.py`)

**What it does:** Serializes and deserializes the full inference pipeline: imputer, outlier handler, feature engineer, encoder, scaler, feature selector, and model. `transform()` turns raw patient data into the feature matrix; `predict()` and `predict_proba()` return class and probabilities.

**Why it exists:** Training and inference must use identical preprocessing. The bundle guarantees that—no drift between training and production.

**Connections:** Built by `run_evaluation.py` from PipelineResult + best model; loaded by engine for every prediction.

**Technologies:** joblib, pandas, numpy.

---

### 4. **RecommendationGenerator** (`recommendation/recommendation_generator.py`)

**What it does:** Maps ML prediction (down/up/steady/no) to clinical recommendations. Applies glucose zones (hypo → stop insulin), IOB stacking checks, high-glucose-without-IOB sanity checks, and activity-based dose reduction. Computes adjustment score and dose_change_units. Flags high-risk when confidence is low or entropy is high.

**Why it exists:** Raw ML output is not clinically safe. The generator adds domain rules that the model doesn’t have (e.g., IOB, glucose zones) and prevents dangerous suggestions.

**Connections:** Called by engine after prediction; uses RecommendationConfig and glucose zones from config.

**Technologies:** Python dataclasses, config-driven logic.

---

### 5. **Data Processing Pipeline** (`data_processing/pipeline.py`)

**What it does:** Loads CSV → optional EDA → imputation → outlier handling → feature engineering (interactions, polynomials, aggregates) → encoding → scaling → feature selection → temporal or random split. Returns PipelineResult with train/val/test and fitted components.

**Why it exists:** Ensures consistent, reproducible preprocessing for training and inference. Centralizes schema, bounds, and feature engineering.

**Connections:** Used by `run_evaluation.py` to produce PipelineResult; InferenceBundle stores the fitted components for inference.

**Technologies:** pandas, scikit-learn, DataSchema, ClinicalBounds.

---

### 6. **Storage** (`storage/db.py`)

**What it does:** SQLite database for records, alerts, glucose readings, dose events, patient context, notifications, settings. Provides init_db, insert_record, get_records, get_alerts, resolve_alert, etc.

**Why it exists:** Persists prediction history, alerts, and UI state. Enables audit and reporting.

**Connections:** Used by API routes for records, alerts, trends, patient context, settings.

**Technologies:** SQLite, Python sqlite3.

---

### 7. **Audit** (`safety/audit.py`)

**What it does:** Logs every prediction/recommendation to `outputs/audit/predictions.jsonl` with timestamp, endpoint, predicted_class, confidence, is_high_risk.

**Why it exists:** Compliance and traceability. Enables post-hoc analysis and debugging.

**Connections:** Called by routes after successful prediction/recommendation.

**Technologies:** JSONL, Python logging.

---

### 8. **Explainability** (`explainability/`)

**What it does:** SHAPExplainer fits on background data, computes local SHAP values, top drivers, and counterfactual scenarios. Maps feature names to clinical labels for display.

**Why it exists:** Clinicians need to understand *why* the system suggested a change. SHAP provides interpretable, instance-level explanations.

**Connections:** Used by engine when X_background is available; returns explanation_drivers and alternative_scenarios for the API response.

**Technologies:** SHAP, numpy.

---

### 9. **Frontend** (`frontend/`)

**What it does:** React SPA with Dashboard (patient input, get recommendation), Reports (records), Insulin Management, Alerts, Model Info, Glucose Trends. Uses ClinicalContext, Recharts for charts, jsPDF for reports.

**Why it exists:** Provides a clinician-oriented UI for entering data and viewing recommendations, explanations, and trends.

**Connections:** Calls `/api/*` endpoints; displays responses with disclaimers and high-risk banners.

**Technologies:** React 18, Vite 5, React Router, Recharts, jsPDF.

---

### 10. **Config** (`config/schema.py`)

**What it does:** Defines DataSchema, ClinicalBounds, PipelineConfig, RecommendationConfig, GLUCOSE_ZONES, and other settings. Single source of truth for column names, bounds, and recommendation content.

**Why it exists:** Avoids hardcoding; supports testability and future customization (e.g., i18n, different thresholds).

**Connections:** Used by pipeline, recommendation generator, API, and domain validation.

**Technologies:** Python dataclasses.

---

## STEP 4 — Technical Concepts Simplification

### Concept 1: F1-Weighted Score

| Audience | Explanation |
|----------|-------------|
| **Developer** | F1-weighted is the macro average of per-class F1 scores, weighted by class support. It balances precision and recall across all classes (down, up, steady, no) and is robust to class imbalance. Formula: `F1_weighted = Σ (support_i × F1_i) / Σ support_i`. |
| **Stakeholder** | F1-weighted measures how well the model predicts all four insulin-change categories, accounting for how often each category appears. Higher is better; 60% means the model is correct more often than random but still has room to improve. |
| **Simple** | It’s like a report card that grades the model on all types of answers (increase, decrease, stay same, no change). 60% means it’s doing better than guessing, but not perfect. |

---

### Concept 2: SHAP (SHapley Additive exPlanations)

| Audience | Explanation |
|----------|-------------|
| **Developer** | SHAP assigns each feature a contribution (Shapley value) to the prediction for a given instance. It satisfies local accuracy and consistency. We use TreeExplainer for tree models or KernelExplainer with a background sample. |
| **Stakeholder** | SHAP shows which patient factors (e.g., glucose, HbA1c) pushed the prediction up or down. It answers “why did the system suggest increasing the dose?” with concrete, interpretable drivers. |
| **Simple** | Imagine a pie chart of reasons: “Your high glucose added 30% to the suggestion to increase; your low activity added 10%.” SHAP does that mathematically for each factor. |

---

### Concept 3: Insulin on Board (IOB) Stacking

| Audience | Explanation |
|----------|-------------|
| **Developer** | IOB is the estimated active insulin still in the body. Stacking occurs when we add more insulin while previous doses are still active, increasing hypoglycemia risk. We check: if glucose ≥ 180, trend is down, and IOB ≥ 0.02 mL, we withhold or reduce correction. |
| **Stakeholder** | When blood sugar is high but insulin from a recent dose is still working, adding more can cause a dangerous low later. The system detects this and holds back or reduces the suggested correction. |
| **Simple** | Like not adding more fuel when the tank is already full—adding more insulin when some is still active can make blood sugar drop too low. The system avoids that. |

---

### Concept 4: InferenceBundle

| Audience | Explanation |
|----------|-------------|
| **Developer** | A serialized object containing fitted preprocessors (imputer, encoder, scaler, feature selector, etc.) and the trained model. Ensures inference uses the exact same transform pipeline as training. |
| **Stakeholder** | The “saved model” is actually the full prediction pipeline—not just the algorithm, but all the data-cleaning and feature steps. This keeps predictions consistent with how the model was trained. |
| **Simple** | It’s the complete recipe: how we clean the data, which numbers we use, and how we get the final answer. Everything is saved together so it works the same every time. |

---

### Concept 5: Glucose Zones

| Audience | Explanation |
|----------|-------------|
| **Developer** | Clinical thresholds (e.g., &lt;70 hypo, 70–90 low-normal, 90–130 target, 131–180 mild hyper, etc.) used for interpretation and override logic. `get_glucose_zone(gl)` returns the zone dict; RecommendationGenerator uses it for hypo override and context. |
| **Stakeholder** | Standard ranges (e.g., 90–130 = target) that guide both interpretation and safety overrides. Below 70, the system stops insulin logic and recommends carbs first. |
| **Simple** | Like traffic lights: green (target), yellow (caution), red (danger). Below 70 is “stop—treat low first before any insulin.” |

---

## STEP 5 — Results and Output Interpretation

### Model Comparison Metrics (`outputs/models/model_comparison.csv`, `outputs/evaluation/evaluation_summary.csv`)

| Metric | Meaning | Why It Matters | Good vs Bad | Decision |
|--------|---------|----------------|-------------|----------|
| **accuracy** | % of correct predictions | Overall correctness | Good: &gt;60%. Bad: &lt;40% | Use for quick sanity check; prefer F1 for imbalanced data |
| **f1_weighted** | Balanced performance across classes | Handles class imbalance | Good: &gt;0.55. Bad: &lt;0.40 | Primary model selection metric |
| **f1_macro** | Unweighted average F1 | Fair to minority classes | Good: &gt;0.40. Bad: &lt;0.30 | Use when minority classes matter |
| **roc_auc_weighted** | Area under ROC curve (OvR) | Ranking/calibration | Good: &gt;0.70. Bad: &lt;0.60 | Use for probability quality |
| **precision_weighted** | Correct when predicting positive | Fewer false alarms | Good: &gt;0.55 | Use when false positives are costly |
| **recall_weighted** | Correct when actual positive | Fewer misses | Good: &gt;0.55 | Use when false negatives are costly |

**Current best (Gradient Boosting):** f1_weighted ≈ 0.60, roc_auc_weighted ≈ 0.77. Solid but improvable with more data or tuning.

---

### API Response Fields

| Field | Meaning | Good vs Bad | Decision |
|-------|---------|-------------|----------|
| **predicted_class** | down / up / steady / no | N/A | Use as starting point; always validate with clinical rules |
| **confidence** | Probability of predicted class | Good: &gt;0.75. Bad: &lt;0.60 | Low confidence → flag for review |
| **is_high_risk** | Flag for clinician review | Good: false. Bad: true | When true, require extra verification |
| **dose_change_units** | Suggested change in units | Depends on context | Cross-check with IOB, trend, activity |
| **uncertainty_entropy** | How spread out probabilities are | Good: &lt;1.0. Bad: &gt;1.0 | High entropy → multiple plausible options |
| **explanation_drivers** | Top factors influencing prediction | More drivers = more transparency | Use to explain to patient or team |

---

### Audit Log (`outputs/audit/predictions.jsonl`)

Each line: `timestamp`, `endpoint`, `request_id`, `predicted_class`, `confidence`, `is_high_risk`.

- **Use:** Traceability, debugging, compliance.
- **Good:** All predictions logged with consistent schema.
- **Bad:** Missing fields, corrupted lines.
- **Decision:** Monitor for anomalies; use for model performance over time.

---

## STEP 6 — Step-by-Step Guided Pitch

### 1. Hook

*"What if a clinician could get an instant, evidence-based suggestion for insulin dosing—with clear explanations and safety checks—while still making the final call?"*

### 2. Problem Statement

Type 1 diabetes requires constant insulin dosing decisions. Clinicians must weigh glucose, diet, activity, HbA1c, and more. Mistakes can cause dangerous highs or lows. There’s a need for tools that support—not replace—clinical judgment.

### 3. Current Challenges

- Manual calculation is time-consuming and error-prone.
- Many factors interact (glucose, IOB, trend, activity).
- Insulin stacking can cause hypoglycemia.
- Clinicians want to understand *why* a suggestion was made.

### 4. Proposed Solution

Glucosense: an ML-powered clinical decision support system that predicts insulin adjustment direction, turns it into concrete recommendations, applies safety rules (glucose zones, IOB stacking), and explains each suggestion. All recommendations require clinician review.

### 5. How the System Works

Clinicians enter patient data in a web dashboard. A Gradient Boosting model predicts one of four outcomes: increase, decrease, maintain, or no change. A recommendation engine applies clinical rules—for example, suspending insulin when glucose is low and recommending carbs, or withholding correction when there’s significant IOB and a downward trend. Each suggestion includes confidence, a high-risk flag when uncertain, and SHAP-based explanations.

### 6. Key Technologies

- **Backend:** Python, FastAPI, scikit-learn, XGBoost.
- **Explainability:** SHAP.
- **Frontend:** React, Vite, Recharts.
- **Persistence:** SQLite, joblib, JSONL audit log.

### 7. System Workflow

Data in → validation → preprocessing (same as training) → model prediction → recommendation engine (safety rules) → explanation → response. All predictions are logged for audit.

### 8. Results and Impact

- Best model: ~60% F1-weighted, ~77% ROC-AUC.
- Safety overrides for hypoglycemia and insulin stacking.
- Full audit trail and high-risk flagging.
- Explainable recommendations for clinician trust.

### 9. Real-World Benefits

- Faster, more consistent dosing support.
- Fewer dangerous stacking errors.
- Transparent reasoning for each suggestion.
- Audit trail for compliance and quality improvement.

### 10. Future Improvements

- More training data and population-specific models.
- Cost-sensitive learning for critical classes.
- Integration with CGM and pump data.
- Continuous monitoring and model retraining.

---

## STEP 7 — Audience Adaptation

### 1. Developer Explanation

Glucosense is a FastAPI backend plus React frontend for Type 1 diabetes decision support. The ML pipeline uses a DataProcessingPipeline (load → impute → outliers → feature engineering → encode → scale → feature selection → temporal split) to produce train/val/test sets. We train multiple classifiers (Logistic Regression, Decision Tree, Random Forest, Gradient Boosting/XGBoost, SVM, MLP, RNN) and select the best by F1-weighted. The winner (currently Gradient Boosting) is serialized as an InferenceBundle (preprocessors + model) via joblib. At inference, the API validates input with Pydantic, transforms via the bundle, predicts, then runs RecommendationGenerator for clinical overrides (glucose zones, IOB stacking, activity). SHAP provides local explanations when background data is available. Records and audit logs go to SQLite and JSONL. The frontend proxies to the API and displays recommendations with disclaimers and high-risk banners.

### 2. Stakeholder Explanation

Glucosense helps clinicians manage Type 1 diabetes by combining machine learning with clinical rules. Clinicians enter patient data and receive dosage suggestions with confidence scores and explanations. The system applies safety checks—for example, it won’t suggest more insulin when the patient is already low or when there’s a risk of insulin stacking. When the model is uncertain, it flags the recommendation for review. All suggestions are logged for audit. The goal is to support faster, safer decisions while keeping the clinician in control.

### 3. Friend / Non-Technical Explanation

Imagine an app that helps doctors decide how much insulin to give a diabetes patient. The doctor types in things like blood sugar, age, and activity level. The app suggests “increase by 2 units” or “keep it the same” and explains why—e.g., “your blood sugar is high” or “you have a lot of insulin still working.” It also has safety rules: if blood sugar is too low, it says “don’t give insulin, have some sugar first.” And when it’s not sure, it tells the doctor to double-check. The doctor always makes the final decision; the app is there to help.

---

## STEP 8 — Visual Explanation Guidance

### 1. System Architecture Diagram

**Show:** High-level boxes for Frontend, API, Engine, Storage, Audit, Model. Arrows: Frontend → API → Engine; Engine → Model, RecommendationGenerator, SHAP; Engine → Storage, Audit. Label data flow (JSON in, JSON out, DB writes).

### 2. Data Flow Diagram

**Show:** User Input → Validation → Transform (Impute → Encode → Scale → Select) → Predict → RecommendationGenerator (Zones, IOB, Activity) → Explain (SHAP) → Response. Parallel: Audit log, SQLite. Use swimlanes for User, API, Engine, Storage.

### 3. Model Pipeline Diagram

**Show:** Raw CSV → Load → EDA (optional) → Impute → Outliers → Feature Engineering → Encode → Scale → Split (temporal) → Train Models → Evaluate (F1-weighted) → Save Best → InferenceBundle. Emphasize that the same pipeline is used at inference.

### 4. User Interaction Flow

**Show:** Clinician opens Dashboard → Enters patient data → Clicks “Get Recommendation” → API request → Loading state → Response displayed (recommendation, confidence, drivers, disclaimer) → Optional: View Records, Alerts, Trends, Model Info. Include error states (validation, 503 model not loaded).

---

## STEP 9 — Q&A Preparation

### From Developers

**Q: Why Gradient Boosting over Random Forest?**  
A: On our current dataset (with clinical ML pipeline, calibration, and threshold optimization), Gradient Boosting achieved the highest F1-weighted (~60%). Random Forest was competitive; we can re-evaluate with more data or different splits.

**Q: How is preprocessing kept in sync between training and inference?**  
A: The InferenceBundle stores the fitted imputer, encoder, scaler, feature selector, and feature engineer. `bundle.transform(df)` runs the same steps as training. No separate inference pipeline.

**Q: What if the model file is corrupted?**  
A: We check file size and catch EOFError. The API returns 503 with a clear message. The fix is to re-run `python run_evaluation.py` or `python run_pipeline.py`.

**Q: How does SHAP get background data?**  
A: We load reference data from the dashboard data loader (or pipeline). A random sample (e.g., 100 rows) is used as the SHAP background. If unavailable, we fall back to probability-based drivers.

---

### From Stakeholders

**Q: Is this FDA-approved?**  
A: No. This is a decision support tool for use in clinical or research settings. All recommendations require review by a qualified healthcare professional. Regulatory approval would require additional validation and compliance steps.

**Q: What’s the accuracy?**  
A: The best model achieves ~60% F1-weighted and ~77% ROC-AUC. We use F1 because classes are imbalanced. There’s room to improve with more data and tuning.

**Q: How do you prevent dangerous recommendations?**  
A: We use glucose zones (e.g., below 70 → stop insulin, recommend carbs), IOB stacking checks, and high-risk flagging when confidence is low. The clinician always makes the final decision.

**Q: Can we integrate with our EHR?**  
A: The API is REST-based. Integration would require an adapter to map EHR data to our PatientInput schema and to consume our JSON responses. We don’t currently provide an EHR connector.

---

### From Investors

**Q: What’s the market opportunity?**  
A: Type 1 diabetes management is a large market. Decision support tools can reduce clinician workload, improve consistency, and potentially reduce adverse events. Glucosense focuses on explainability and safety, which differentiates it from black-box solutions.

**Q: What’s the technical moat?**  
A: The combination of ML + clinical rules, SHAP explainability, and a full audit trail. The pipeline is reproducible and configurable. We can extend to more data sources and populations.

**Q: What are the main risks?**  
A: Model performance depends on training data; generalization to new populations needs validation. Regulatory path is unclear. Bias and fairness should be evaluated per deployment.

---

### From Curious Friends

**Q: Does it replace the doctor?**  
A: No. It suggests; the doctor decides. It’s like a calculator for insulin—helpful but not a substitute for judgment.

**Q: What if the app is wrong?**  
A: We flag uncertain recommendations and log everything. The doctor can see the reasoning and override. We also have safety rules (e.g., don’t suggest more insulin when the patient is low).

**Q: Can patients use it themselves?**  
A: It’s built for clinicians. Patients should not use it without medical supervision. Insulin dosing is complex and can be dangerous if done incorrectly.

---

## STEP 10 — Final Speaking Script

### Opening (30 seconds)

*"Glucosense is a clinical decision support system for Type 1 diabetes. It helps clinicians decide whether to increase, decrease, or maintain a patient’s insulin dose—with explanations and safety checks—while the clinician always makes the final call."*

### Problem (45 seconds)

*"Managing Type 1 diabetes means constant dosing decisions. Clinicians consider blood glucose, diet, activity, HbA1c, and more. It’s time-consuming and error-prone. Adding insulin when there’s already a lot in the body can cause dangerous lows. Missing a needed increase can leave patients too high. Clinicians need support that’s fast, transparent, and safe."*

### Solution (60 seconds)

*"Glucosense combines machine learning with clinical rules. A clinician enters patient data—glucose, age, HbA1c, activity, and optional fields like insulin on board and anticipated carbs. A trained model predicts one of four outcomes: increase, decrease, maintain, or no change. A recommendation engine then applies safety rules. If glucose is below 70, we stop insulin logic and recommend 15 grams of fast-acting carbs first. If blood sugar is high but there’s significant insulin still active and a downward trend, we withhold or reduce the correction to avoid stacking. We also adjust for high physical activity. Each suggestion includes confidence and a high-risk flag when the system is uncertain. We use SHAP to explain which factors drove the prediction. Everything is logged for audit."*

### How It Works (45 seconds)

*"The system has a React frontend and a FastAPI backend. The model is trained on historical data with a full preprocessing pipeline—imputation, encoding, scaling, feature selection. The best model by F1 score is saved as a bundle that includes all preprocessing steps. At inference, we run the same pipeline, predict, apply clinical rules, and optionally compute SHAP explanations. Records go to SQLite; predictions go to an audit log. The UI shows recommendations, trends, alerts, and model info."*

### Results (30 seconds)

*"Our best model achieves about 60% F1-weighted and 77% ROC-AUC. We have safety overrides for hypoglycemia and insulin stacking. We flag high-risk recommendations. And we provide explanations so clinicians can understand and trust the suggestions."*

### Closing (20 seconds)

*"Glucosense is a support tool, not a replacement for clinical judgment. Every recommendation must be reviewed by a qualified healthcare professional. We’re focused on making dosing decisions faster, safer, and more transparent. Thank you."*

---

*End of Project Explanation Guide*
