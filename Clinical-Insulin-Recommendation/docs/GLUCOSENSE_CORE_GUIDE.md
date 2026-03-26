# GlucoSense — Core Technical Guide

**ML Pipeline | Prediction | Dose Suggestions | Safety Criteria**

---

## 1. ML Pipeline

### 1.1 Overview

There are **two training stories** in this workspace:

1. **Clinical CDS bundle (legacy `insulin_system`)** — Trains classifiers for insulin **adjustment direction** (down / up / steady / no) from the **`DataSchema`** feature set. The winning model is saved to **`outputs/best_model/`** and loaded by **`POST /api/recommend`**. The **`DataProcessingPipeline`** expects the **legacy CSV columns** (`Insulin`, `patient_id`, `gender`, etc.). See **`data/README.md`**.

2. **Smart Sensor ML (`smart_sensor_ml`)** — Separate package for **`data/SmartSensor_DiabetesMonitoring.csv`**: predicts **Insulin_Dose tiers** (Low / Moderate / High) with patient-group splits, writes **`outputs/smart_sensor_ml/`** and a PDF report. Run **`scripts/run_smart_sensor_ml.py`**. Not connected to the recommend API unless you add an adapter.

Workspace pipeline map: **`SYSTEM_PIPELINE.md`** (repo root).

### 1.2 Legacy clinical pipeline steps (`insulin_system` + `scripts/pipeline/`)

| Step | Description |
|------|-------------|
| **Load** | Load legacy-format CSV (see `DataSchema`); target column **`Insulin`** (direction classes) |
| **EDA** | Optional exploratory analysis; plots to `outputs/eda/` |
| **Imputation** | Fill missing numeric (median) and categorical (mode) values |
| **Outlier handling** | Clip values to clinical bounds (age, glucose, BMI, etc.) |
| **Feature engineering** | Add interaction terms (e.g. glucose×insulin_sensitivity, BMI×activity), derived categoricals |
| **Encoding** | One-hot encode categoricals (gender, food_intake, etc.) with drop_first |
| **Scaling** | StandardScaler for numeric features |
| **Feature selection** | Select features for model input (mutual information, etc.) |
| **Split** | Temporal or random stratified split (train/val/test) |
| **Train** | Multiple models: Logistic Regression, Decision Tree, Random Forest, **Gradient Boosting**, Extra Trees, SVM, MLP, RNN/LSTM |
| **Evaluate** | F1-weighted, ROC-AUC, precision, recall per class |
| **Select best** | Highest F1-weighted → save to `outputs/best_model/inference_bundle.joblib` |

### 1.3 Current Best Model

- **Model:** Gradient Boosting (XGBoost)
- **F1-weighted:** ~60%
- **ROC-AUC:** ~77%
- **Calibration:** Sigmoid
- **Threshold optimization:** Yes

### 1.4 Running the Pipeline

```bash
# Full pipeline (all models, ~5–10 min)
python run_pipeline.py

# Quick (Gradient Boosting + Random Forest, ~2 min)
python run_pipeline.py --no-eda --models gradient_boosting random_forest

# Clinical ML pipeline (calibration, threshold optimization)
python run_clinical_ml_improvement.py
```

---

## 2. How Prediction Works

### 2.1 Flow

1. **Input** — API receives JSON (glucose, age, gender, food_intake, activity, BMI, HbA1c, etc.)
2. **Validation** — Pydantic validates ranges; builds `PatientInput` → single-row DataFrame
3. **Transform** — `InferenceBundle.transform(df)` runs same preprocessing as training:
   - Impute → Outlier handling → Feature engineering → Encode → Scale → Feature select
4. **Predict** — `bundle.predict(X)` → predicted class (down/up/steady/no)
5. **Probabilities** — `bundle.predict_proba(X)` → confidence, entropy, probability breakdown
6. **Response** — `predicted_class`, `confidence`, `uncertainty_entropy`, `probability_breakdown`

### 2.2 Inference Bundle

The bundle (`outputs/best_model/inference_bundle.joblib`) contains:
- Imputer, OutlierHandler, FeatureEngineer, Encoder, Scaler, FeatureSelector
- Trained model (e.g. Gradient Boosting)
- Same transform pipeline as training → no drift

### 2.3 Output Classes

| Class | Meaning |
|-------|---------|
| **down** | Reduce dose |
| **up** | Increase dose |
| **steady** | Maintain current dose |
| **no** | No change needed |

---

## 3. How Dose Suggestions Are Calculated

### 3.1 Adjustment Score (0–1)

```
score = 0.4×(glucose/150) + 0.3×(1−activity/10) + 0.3×(HbA1c/10)
```
Clipped to [0, 1]. Higher glucose → higher score; higher activity → lower score.

### 3.2 Dose Change Units

| Predicted class | Formula |
|-----------------|---------|
| **up** | `round(score × max_adjustment)` → 1 to max |
| **down** | `-round(score × max_adjustment)` → -max to -1 |
| **steady** / **no** | 0 units |

**Max adjustment** is personalized by weight (Uganda guideline):
- Default max: 5 units
- Lighter patients: lower cap (e.g. 50 kg → ~3, 70 kg → ~4, 90 kg+ → 5)

### 3.3 Meal Bolus

```
meal_bolus_units = anticipated_carbs (g) ÷ ICR
```
Default ICR: 10 (1 unit per 10 g carbs).

### 3.4 Correction Dose

```
correction_dose_units = (glucose − target) ÷ ISF
```
Target: 100 mg/dL. Default ISF: 50. Only when glucose > target.

---

## 4. Safety Criteria

### 4.1 Hard Stops

| Condition | Action |
|-----------|--------|
| **Glucose < 54 mg/dL** (Level 2 hypo) | STOP insulin. Suggest 20 g fast-acting carbs. |
| **Glucose 54–69 mg/dL** (Level 1 hypo) | STOP insulin. Suggest 15 g fast-acting carbs. |
| **Glucose ≥ 180 + IOB ≥ 0.02 + trend down** | Withhold or reduce correction (insulin stacking risk) |
| **Glucose ≥ 131 + IOB = 0 + model says reduce** | Override to maintain (high glucose + no IOB → correction may be needed) |
| **Glucose 70–90** (low-normal) | No dose increase allowed |
| **Activity ≥ 7 + dose increase** | Reduce suggested increase by 20% |

### 4.2 Uganda Daily Dose Cap

- Max daily: 1.5 IU/kg (adults & children ≥5); 0.5 IU/kg (children <5)
- Suggested increase capped to stay within headroom

### 4.3 High-Risk Flagging

| Condition | Action |
|-----------|--------|
| Confidence < 0.75 | Flag for clinician review |
| Uncertainty entropy > 1.0 | Flag for clinician review |
| CGM sensor error | Flag; require manual finger-stick |
| Ketones moderate/large/high | Flag; verify before dosing |
| Age < 5 years | Flag; Uganda: refer to paediatrician |

### 4.4 Configuration

All thresholds in `config/clinical_thresholds.json`:
- Glucose zones, ICR/ISF bounds, CDS safety
- Adjustment score weights, magnitude thresholds
- Activity and stacking risk parameters

---

## 5. End-to-End Flow

```
Patient data → Validation → Transform → Model predict → RecommendationGenerator
    → Safety overrides → Dose units + meal bolus + correction → High-risk flag
    → SHAP explanation (optional) → API response → Frontend display
```

---

*See also: GLUCOSENSE_SYSTEM_DOCUMENTATION.md, PROJECT_EXPLANATION_GUIDE.md*
