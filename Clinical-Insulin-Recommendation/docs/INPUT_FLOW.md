# GlucoSense Input and Recommendation Flow

This document describes how user input flows through the system from the UI to the ML model and back to the user.

## 1. Input flow (end-to-end)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FRONTEND (Dashboard)                                                        │
│  Core inputs: age, gender, glucose_level, food_intake, previous_medications  │
│  Optional: BMI, HbA1c, weight (others omitted; pipeline imputes)             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  CLIENT VALIDATION                                                           │
│  validateForm() → field errors shown inline; buildBody() builds JSON          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼  POST /api/recommend
┌─────────────────────────────────────────────────────────────────────────────┐
│  API LAYER (routes.py)                                                        │
│  validate_patient_input(body) → (PatientInput, warnings, errors)             │
│  If errors → 422 with structured errors                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DOMAIN VALIDATION (domain/validation.py)                                     │
│  validate_assessment_input(body) → (sanitized_body, errors)                   │
│  Required: age, gender, glucose_level, food_intake, previous_medications     │
│  Optional: BMI, HbA1c, weight, physical_activity, etc. (imputed if missing) │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  SCHEMA → DATAFRAME (validators.patient_input_to_dataframe)                   │
│  PatientInput.to_row_dict() → single-row dict → pd.DataFrame([row])          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  INFERENCE BUNDLE (persistence/bundle.py)                                     │
│  transform(df):                                                               │
│    - Coerce numeric columns to float (avoids dtype errors)                    │
│    - Imputer fills missing numerics/categoricals                              │
│    - OutlierHandler clips to clinical bounds                                 │
│    - FeatureEngineer (interactions, polynomial, aggregates, temporal)         │
│    - Encoder (categoricals) → Scaler → FeatureSelector                       │
│  → X (numpy array, float64)                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ML MODEL (saved best model in bundle)                                        │
│  predict(X) → predicted_class (down | up | steady | no)                      │
│  predict_proba(X) → probability vector                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  RECOMMENDATION (api/engine.run_recommend)                                    │
│  RecommendationGenerator(config).generate(pred, confidence, entropy, probs)   │
│  Config holds: confidence_threshold, uncertainty_entropy_threshold,            │
│               recommendation_content (class → summary/action/detail)         │
│  Optional: MLflow metrics logged if mlflow is active                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  RESPONSE & SIDE EFFECTS                                                      │
│  - RecommendationResponse (dosage_action, summary, is_high_risk, etc.)       │
│  - insert_record() for audit                                                  │
│  - insert_glucose_reading(glucose_level) for trends                          │
│  - upsert_patient_context() for sidebar                                      │
│  - Critical alert detection (if glucose or risk triggers)                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. Core vs optional inputs

| Input              | Required | Notes                                      |
|--------------------|----------|--------------------------------------------|
| age                | Yes      | 0–100                                      |
| gender             | Yes      | Male, Female                               |
| glucose_level      | Yes      | Primary clinical signal (mg/dL)             |
| food_intake        | Yes      | Low, Medium, High                          |
| previous_medications | Yes    | None, Insulin, Oral                        |
| medication_name    | If Oral  | Required when previous_medications = Oral   |
| BMI, HbA1c, weight | No       | Shown in form; pipeline imputes if missing |
| physical_activity, insulin_sensitivity, sleep_hours, creatinine, family_history | No | Not shown; imputed by pipeline |

## 3. Alert flow (critical conditions)

After a recommendation (or when new glucose is recorded):

1. **Alert detection** uses configurable thresholds (e.g. glucose &lt; 70 or &gt; 400, or is_high_risk).
2. Critical conditions insert rows into the **alerts** table.
3. **GET /api/alerts** returns active alerts; UI shows them in the Alerts page and notification dropdown (e.g. “Go to Alerts”).

## 4. Configuration sources

- **Domain constants**: `domain/constants.py` (AGE_MIN/MAX, GENDER_VALUES, etc.).
- **Recommendation**: `config/schema.RecommendationConfig` (thresholds, recommendation_content).
- **Data schema**: `config/schema.DataSchema` (column names, NUMERIC, CATEGORICAL).
- **Clinical bounds**: `config/schema.ClinicalBounds` (min/max for outlier clipping).

All recommendation text and thresholds are config-driven; the ML model only outputs class and probabilities.
