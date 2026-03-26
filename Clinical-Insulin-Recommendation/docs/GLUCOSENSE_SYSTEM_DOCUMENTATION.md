# GlucoSense — Complete System Documentation

**Clinical Decision Support System for Type 1 Diabetes Management**

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Technology Stack](#2-technology-stack)
3. [Technologies, Tools & Rationale](#3-technologies-tools--rationale)
4. [System Architecture](#4-system-architecture)
5. [Full Functionality](#5-full-functionality)
6. [API Reference](#6-api-reference)
7. [Data Flow & Processing Pipeline](#7-data-flow--processing-pipeline)
8. [Safety Engine & Clinical Guidelines](#8-safety-engine--clinical-guidelines)

---

## 1. System Overview

### 1.1 Purpose

GlucoSense is a **clinical decision support (CDS) system** for Type 1 diabetes that combines **machine learning predictions** with **clinical rules** and **safety checks** to assist clinicians in insulin dosing decisions. It does **not** replace clinical judgment—every recommendation requires review by a qualified healthcare professional.

### 1.2 Problem Addressed

- Type 1 diabetes requires constant insulin dosing decisions based on glucose, diet, activity, HbA1c, and other factors.
- Manual calculation is time-consuming and error-prone.
- Insulin stacking (adding insulin when previous doses are still active) can cause hypoglycemia.
- Clinicians need support that is fast, transparent, and safe.

### 1.3 Target Users

| User Type | Role |
|-----------|------|
| **Primary** | Clinicians and healthcare staff managing Type 1 diabetes patients |
| **Secondary** | Researchers evaluating ML-assisted dosing support |

### 1.4 Core Capabilities

| Capability | Description |
|------------|-------------|
| **Prediction** | ML model predicts insulin adjustment direction: down, up, steady, or no |
| **Recommendation** | Converts predictions into concrete dosage suggestions with magnitude, confidence, and high-risk flags |
| **Explainability** | SHAP-based explanations show which factors drove the prediction |
| **Safety** | CDS Safety Engine with hard stops for hypoglycemia, IOB stacking, CGM errors |
| **Audit** | All predictions logged to JSONL; records stored in SQLite |

---

## 2. Technology Stack

### 2.1 Summary Table

| Layer | Technologies |
|-------|--------------|
| **Frontend** | React 18, Vite 5, React Router, Recharts, jsPDF, react-icons |
| **Backend** | Python 3.9+, FastAPI, Uvicorn, Pydantic |
| **ML & Data** | scikit-learn, XGBoost, LightGBM, CatBoost, imbalanced-learn, Optuna |
| **Explainability** | SHAP |
| **Persistence** | SQLite, joblib, JSONL |
| **Data Processing** | pandas, numpy |

### 2.2 Backend Dependencies (requirements.txt)

```
numpy>=1.21.0
pandas>=1.5.0
scikit-learn>=1.2.0
matplotlib>=3.5.0
seaborn>=0.12.0
pytest>=7.0.0
xgboost>=1.6.0
lightgbm>=3.3.0
catboost>=1.2.0
imbalanced-learn>=0.10.0
optuna>=3.0.0
shap>=0.43.0
joblib>=1.2.0
jupyter>=1.0.0
nbconvert>=7.0.0
uvicorn[standard]>=0.24.0
fastapi>=0.109.0
slowapi>=0.1.9
```

### 2.3 Frontend Dependencies (package.json)

```
react ^18.2.0
react-dom ^18.2.0
react-router-dom ^6.22.0
recharts ^2.12.0
react-icons ^5.0.0
jspdf ^4.2.0
jspdf-autotable ^5.0.7
vite ^5.1.0
@vitejs/plugin-react ^4.2.1
```

---

## 3. Technologies, Tools & Rationale

### 3.1 Backend

| Technology | Purpose | Why Chosen |
|------------|---------|------------|
| **Python 3.9+** | Runtime | Dominant language for ML/data science; rich ecosystem for healthcare and scientific computing |
| **FastAPI** | Web framework | High performance, automatic OpenAPI docs, built-in validation with Pydantic, async support |
| **Uvicorn** | ASGI server | Fast, production-ready ASGI server for FastAPI |
| **Pydantic** | Validation | Type-safe request/response schemas; automatic validation and serialization |
| **slowapi** | Rate limiting | Protects API from abuse; optional when installed |

### 3.2 Machine Learning

| Technology | Purpose | Why Chosen |
|------------|---------|------------|
| **scikit-learn** | Core ML | Industry standard; pipelines, preprocessing, model selection, evaluation |
| **XGBoost** | Gradient boosting | State-of-the-art for tabular data; often best for structured clinical data |
| **LightGBM** | Gradient boosting | Fast training; alternative for large datasets |
| **CatBoost** | Gradient boosting | Handles categorical features natively |
| **imbalanced-learn** | Class imbalance | SMOTE, class weights for imbalanced insulin adjustment classes |
| **Optuna** | Hyperparameter tuning | Bayesian optimization; efficient search over model parameters |
| **joblib** | Model serialization | Standard for scikit-learn; efficient serialization of numpy arrays and fitted objects |

### 3.3 Explainability

| Technology | Purpose | Why Chosen |
|------------|---------|------------|
| **SHAP** | Model explainability | Gold standard for interpretable ML; Shapley values provide theoretically grounded feature contributions; TreeExplainer for tree models |

### 3.4 Data Processing

| Technology | Purpose | Why Chosen |
|------------|---------|------------|
| **pandas** | Data manipulation | De facto standard for tabular data; DataFrame operations, merging, grouping |
| **numpy** | Numerical computing | Fast array operations; foundation for ML libraries |
| **matplotlib / seaborn** | Visualization | EDA plots, confusion matrices, ROC curves during pipeline |

### 3.5 Persistence

| Technology | Purpose | Why Chosen |
|------------|---------|------------|
| **SQLite** | Application database | Zero-config, file-based; stores records, alerts, patients, glucose readings, dose events, settings |
| **JSONL** | Audit log | Append-only; one JSON object per line; easy to parse and stream for compliance |

### 3.6 Frontend

| Technology | Purpose | Why Chosen |
|------------|---------|------------|
| **React 18** | UI framework | Component-based; large ecosystem; suitable for complex clinical UIs |
| **Vite 5** | Build tool | Fast HMR; modern ESM-based dev server; minimal config |
| **React Router 6** | Routing | Client-side routing for SPA; nested routes |
| **Recharts** | Charts | React-native charting; glucose trends, model metrics |
| **jsPDF + jspdf-autotable** | PDF export | Generate reports (records, recommendations) for download |
| **react-icons** | Icons | Large icon set; consistent styling |

---

## 4. System Architecture

### 4.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React + Vite)                                  │
│  Dashboard │ Patients │ Recommendation │ Reports │ Insulin Mgmt │ Alerts │       │
│  Model Info │ Glucose Trends │ Settings                                           │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ HTTP /api/*
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         API LAYER (FastAPI on port 8000)                         │
│  POST /predict, /explain, /recommend, /batch-recommend, /feedback, /dose          │
│  GET /model-info, /records, /alerts, /patients, /glucose-trends, /settings       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              ENGINE (api/engine.py)                               │
│  InferenceBundle (transform + predict) → RecommendationGenerator → Response      │
│  Optional: SHAPExplainer for explanation_drivers, alternative_scenarios           │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
            ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
            │ SQLite DB    │    │ Audit JSONL  │    │ Best Model   │
            │ records,     │    │ predictions  │    │ (joblib)     │
            │ alerts,      │    │              │    │              │
            │ patients,    │    │              │    │              │
            │ glucose,     │    │              │    │              │
            │ dose_events  │    │              │    │              │
            └──────────────┘    └──────────────┘    └──────────────┘
```

### 4.2 Component Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              DATA PROCESSING PIPELINE                             │
│  CSV Load → EDA (optional) → Impute → Outliers → Feature Engineering →           │
│  Encode → Scale → Feature Selection → Temporal Split → Train Models               │
└──────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              INFERENCE BUNDLE (joblib)                             │
│  Imputer + OutlierHandler + FeatureEngineer + Encoder + Scaler +                   │
│  FeatureSelector + Model (e.g. Gradient Boosting)                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              RECOMMENDATION GENERATOR                             │
│  Glucose zones (hypo override) → IOB stacking check → Activity adjustment →        │
│  Dose magnitude → High-risk flag (confidence < 0.75 or entropy > 1.0)             │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Directory Structure

```
Glucosense/
├── app.py                    # FastAPI application entry point
├── run_pipeline.py           # ML pipeline: train, evaluate, save best model
├── run_recommendation.py     # Standalone batch recommendation script
├── scripts/windows/run_dev.ps1   # Start backend + frontend (Windows)
├── requirements.txt
├── config/
│   ├── clinical_thresholds.json   # Glucose zones, ICR/ISF bounds, CDS safety
│   └── uganda_t1d_guidelines.json # Daily dose range, regimens, insulin types
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── api.js
│   │   ├── pages/           # Dashboard, Patients, Reports, Alerts, etc.
│   │   ├── components/      # AssessmentForm, RecommendationResult, etc.
│   │   ├── services/        # clinicalApi, dashboardApi, patientsApi
│   │   └── context/        # ClinicalContext
│   └── package.json
├── src/
│   ├── insulin_system/
│   │   ├── api/             # routes, engine, schemas, validators
│   │   ├── config/           # schema, clinical_config
│   │   ├── data_processing/ # pipeline, load, imputation, feature_engineering
│   │   ├── domain/           # constants, validation
│   │   ├── explainability/   # shap_explainer
│   │   ├── persistence/     # bundle (InferenceBundle)
│   │   ├── recommendation/  # recommendation_generator
│   │   ├── safety/          # audit
│   │   └── storage/         # db, patients, backup
│   └── clinical_ml_pipeline/ # Full ML experiment pipeline
├── outputs/
│   ├── best_model/          # inference_bundle.joblib, metadata.json
│   ├── audit/               # predictions.jsonl
│   ├── evaluation/          # Per-model metrics, confusion matrices
│   └── glucosense.db        # SQLite database
└── scripts/                 # test_system_interaction, export_feedback, etc.
```

---

## 5. Full Functionality

### 5.1 Frontend Pages & Features

| Page | Path | Functionality |
|------|------|---------------|
| **Dashboard** | `/` | Patient selection, assessment form (glucose, age, HbA1c, activity, etc.), "Get Recommendation" button, recommendation result display |
| **Patients** | `/patients` | Register patients, view/edit patient details, patient records, backup/restore |
| **Recommendation** | `/recommendation` | Dedicated recommendation flow for selected patient |
| **Reports** | `/reports` | View prediction records, export to PDF |
| **Insulin Management** | `/insulin` | Record dose events (meal bolus, correction, total) |
| **Alerts** | `/alerts` | View and resolve critical alerts (hypo, hyper, high-risk) |
| **Model Info** | `/model-info` | Current model name, F1-weighted, ROC-AUC, feature importance |
| **Glucose Trends** | `/trends` | Chart of glucose readings over time |
| **Settings** | (sidebar) | Units (mg/dL), theme (light/dark), notifications |

### 5.2 Assessment Input Fields

| Field | Type | Description |
|-------|------|-------------|
| `glucose_level` | float | Blood glucose (mg/dL) |
| `age` | int | Patient age (0–100) |
| `gender` | string | Male / Female |
| `food_intake` | string | Low / Medium / High |
| `physical_activity` | float | Activity level (0–10 scale) |
| `BMI` | float | Body mass index |
| `HbA1c` | float | Glycated hemoglobin (%) |
| `weight_kg` | float | Optional; for Uganda dose cap |
| `iob` | float | Insulin on board (mL); optional |
| `anticipated_carbs_g` | float | Anticipated carbohydrates (g); optional |
| `ketone_level` | string | none, trace, small, moderate, large, high |
| `cgm_sensor_error` | boolean | True if CGM reports sensor error |
| `typical_daily_insulin` | float | 7-day average TDD for high-uncertainty check |

### 5.3 Recommendation Output

| Field | Description |
|-------|-------------|
| `predicted_class` | down / up / steady / no |
| `confidence` | Probability of predicted class |
| `uncertainty_entropy` | Spread of probabilities |
| `dosage_action` | Increase / Decrease / Maintain / None |
| `dose_change_units` | Suggested change in units (+/-) |
| `meal_bolus_units` | Meal bolus from ICR |
| `correction_dose_units` | Correction from ISF |
| `system_interpretation` | Human-readable summary |
| `recommended_action` | Full suggested action text |
| `explanation_drivers` | Top SHAP drivers |
| `alternative_scenarios` | Counterfactual scenarios |
| `is_high_risk` | Flag for clinician review |
| `clinical_disclaimer` | Standard disclaimer text |

### 5.4 ML Pipeline Functionality

| Step | Description |
|------|-------------|
| **Load** | Load CSV (`data/SmartSensor_DiabetesMonitoring.csv`); derive insulin dose target |
| **EDA** | Optional exploratory analysis; plots to `outputs/eda/` |
| **Imputation** | Fill missing numeric/categorical values |
| **Outlier handling** | Clip or handle values outside clinical bounds |
| **Feature engineering** | Interactions, polynomials, derived categoricals |
| **Encoding** | One-hot encode categoricals (drop_first) |
| **Scaling** | StandardScaler for numeric features |
| **Feature selection** | Select features for model input |
| **Split** | Temporal or random stratified split (train/val/test) |
| **Train** | Multiple models: Logistic Regression, Decision Tree, Random Forest, Gradient Boosting (XGBoost), SVM, MLP, RNN/LSTM |
| **Evaluate** | F1-weighted, ROC-AUC, precision, recall per class |
| **Select best** | Highest F1-weighted → save to `outputs/best_model/` |

### 5.5 Database Schema (SQLite)

| Table | Purpose |
|------|---------|
| `records` | Prediction/recommendation records (endpoint, predicted_class, confidence, is_high_risk, patient_id) |
| `notifications` | In-app notifications |
| `messages` | Chat/message storage |
| `glucose_readings` | Glucose values for trend chart |
| `dose_events` | Meal bolus, correction, total dose |
| `alerts` | Critical alerts (hypo, hyper, high-risk) |
| `patients` | Registered patients |
| `patient_context` | Current patient context (name, condition, recent metrics) |
| `clinician_feedback` | Override/feedback for model improvement |
| `app_settings` | Units, theme, notifications_enabled |

---

## 6. API Reference

### 6.1 Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/predict` | Get insulin dosage prediction |
| POST | `/api/explain` | Get full explanation (SHAP drivers, counterfactuals) |
| POST | `/api/recommend` | Full recommendation (requires patient_id) |
| POST | `/api/batch-recommend` | Batch recommendations (max 50 patients) |

### 6.2 Model & Info

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/model-info` | Model metadata, F1-weighted, ROC-AUC |
| GET | `/api/feature-importance` | Global feature importance |

### 6.3 Feedback & Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/feedback` | Record clinician override/feedback |
| GET | `/api/feedback` | List feedback records |
| GET | `/api/monitoring/stats` | Recent prediction stats |

### 6.4 Records & Alerts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/records` | List prediction records |
| GET | `/api/alerts` | List alerts (unresolved by default) |
| POST | `/api/alerts/resolve` | Resolve single alert |
| POST | `/api/alerts/resolve-all` | Resolve all alerts |

### 6.5 Patients

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/patients` | List all patients |
| GET | `/api/patients/{id}` | Get patient by ID |
| POST | `/api/patients` | Register new patient |
| PUT | `/api/patients/{id}` | Update patient |
| GET | `/api/patients/{id}/records` | Patient assessment records |
| GET | `/api/patients/{id}/glucose-readings` | Patient glucose readings |
| GET | `/api/patients/{id}/dose-events` | Patient dose events |

### 6.6 Glucose & Context

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/glucose-zones` | Standard glucose zones |
| GET | `/api/glucose-zones/interpret?glucose=120` | Interpret glucose value |
| GET | `/api/glucose-trends` | Glucose readings for chart |
| GET | `/api/patient-context` | Current patient context |

### 6.7 Dose & Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/dose` | Record dose event |
| GET | `/api/settings` | Get app settings |
| PUT | `/api/settings` | Update settings |

### 6.8 Notifications & Backup

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notifications` | List notifications |
| POST | `/api/notifications` | Create notification |
| PATCH | `/api/notifications/read` | Mark all read |
| POST | `/api/backup` | Create DB backup |
| GET | `/api/backups` | List backups |
| POST | `/api/backups/restore` | Restore from backup |

### 6.9 Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check (API + database) |

---

## 7. Data Flow & Processing Pipeline

### 7.1 Request-to-Response Flow (Recommend)

```
1. User enters patient data on Dashboard
2. Frontend POST /api/recommend with JSON body
3. API validates via Pydantic (PatientInput schema)
4. Engine loads InferenceBundle (lazy, cached)
5. patient_input_to_dataframe() → bundle.transform(df)
   - Same pipeline as training: impute → outliers → feature engineering → encode → scale → select
6. bundle.predict(X) → predicted_class
   bundle.predict_proba(X) → probability_breakdown, confidence, entropy
7. RecommendationGenerator.generate(predicted_class, confidence, entropy, patient_dict)
   - Glucose <70 → REJECT insulin, suggest 15g carbs
   - IOB stacking check → withhold/reduce correction
   - High activity → reduce dose
   - is_high_risk if confidence < 0.75 or entropy > 1.0
8. SHAPExplainer (if background available) → explanation_drivers, alternative_scenarios
9. Parallel: log_prediction(), insert_record(), insert_glucose_reading(), check_critical_alerts()
10. Return RecommendationResponse
11. Frontend displays recommendation, confidence, high-risk banner, drivers, disclaimer
```

### 7.2 Inference Bundle Transform Steps

1. **Impute** — Fill missing values (median for numeric, mode for categorical)
2. **Outlier handling** — Clip to clinical bounds
3. **Feature engineering** — Add interaction terms, derived features
4. **Encode** — One-hot encode categoricals
5. **Scale** — StandardScaler
6. **Feature selection** — Select same features as training
7. **Predict** — Model inference

---

## 8. Safety Engine & Clinical Guidelines

### 8.1 Glucose Zones

| Category | Range (mg/dL) | Action |
|----------|---------------|--------|
| Level 2 Hypoglycemia | <54 | Critical |
| Level 1 Hypoglycemia | 54–69 | Critical |
| Target | 70–180 | Normal |
| Hyperglycemia | 181–250 | Warning |
| Critical | >250 or high ketones | Critical |

### 8.2 Hard Stops

| Condition | Action |
|-----------|--------|
| Glucose <70 | REJECT insulin; suggest 15g fast-acting carbs; trigger alert |
| Adjustment >> typical | If dose >2× typical correction (from 7-day TDD), flag high_uncertainty |
| CGM sensor error | Cap confidence at 0.5; require manual finger-stick; add cgm_error flag |
| High ketones | Flag high_ketones; add critical alert |

### 8.3 Uganda Clinical Guideline 2023

- **Daily dose:** 0.6–1.5 IU/kg/day (adults & children ≥5)
- **Children <5:** 0.5 IU/kg/day; refer to paediatrician
- **Regimens:** Basal-bolus (preferred), twice-daily premixed
- **Insulin types:** Short-acting (Actrapid), rapid-acting (Aspart), intermediate (Insulatard), biphasic (Mixtard)

### 8.4 Risk Flags

| Flag | Meaning |
|------|---------|
| `hypoglycemia_alert` | Glucose <70; insulin rejected |
| `high_uncertainty` | Low confidence or adjustment >> typical |
| `cgm_error` | CGM sensor error; finger-stick required |
| `high_ketones` | High ketone levels reported |

### 8.5 Language Constraints

All recommendations use **"The system suggests..."** phrasing. The clinician remains the final decision-maker.

---

## Appendix: Model Performance (Current)

- **Best model:** Gradient Boosting (XGBoost)
- **Selection metric:** F1-weighted
- **F1-weighted:** ~60%
- **ROC-AUC (weighted):** ~77%
- **Models evaluated:** Logistic Regression, Decision Tree, Random Forest, Gradient Boosting, Extra Trees, SVM (RBF), MLP, RNN/LSTM

---

---

## Related Documentation

- **GLUCOSENSE_CORE_GUIDE.md** — ML pipeline, prediction flow, dose calculation, safety criteria
- **PROJECT_EXPLANATION_GUIDE.md** — Presentation and audience adaptation
- **CDS_SAFETY_ENGINE.md** — Clinical decision support safety rules

---

*Document generated from GlucoSense codebase. Last updated: March 2025.*
