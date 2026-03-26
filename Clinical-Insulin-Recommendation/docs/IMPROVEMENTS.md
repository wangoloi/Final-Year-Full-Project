# GlucoSense Improvements Summary

This document describes the improvements implemented and their impact on the system.

---

## 1. Contextual Features as Model Inputs (IOB, Glucose Trend, Anticipated Carbs)

### What Was Done
- **Schema**: Added `CONTEXTUAL_NUMERIC` = (`iob`, `anticipated_carbs`, `glucose_trend_encoded`) to `DataSchema`
- **Load**: `DataLoader.load()` adds these columns with defaults (0, 0, "stable") when missing in training CSV
- **Validation**: `validate()` treats contextual columns as optional at load time
- **Feature Engineering**: Added `glucose_trend_encoded` (stable=0, rising=1, falling=-1) from `glucose_trend` string
- **Imputation**: `MissingValueImputer` handles `iob`, `anticipated_carbs`
- **Outliers**: `OutlierHandler` includes contextual columns with `ClinicalBounds` (IOB 0–5 mL, carbs 0–300 g)
- **Feature Selection**: `DOMAIN_KEEP` includes contextual features so they are not dropped
- **API**: `PatientInput.to_row_dict()` includes `iob`, `anticipated_carbs`, `glucose_trend`
- **Bundle**: `InferenceBundle.transform()` ensures contextual columns exist and are coerced

### Impact
- **ML**: Model can now learn when to withhold correction (e.g., high IOB + falling trend).
- **Training**: Run `python run_evaluation.py` to retrain with new features. Training data uses defaults; inference uses real values.
- **Backward compatibility**: Old models without these features will fail at inference (feature count mismatch). Retraining is required.

---

## 2. Clinical Cost-Sensitive Evaluation

### What Was Done
- **Config**: Added `CLINICAL_COST_MATRIX` dict: cost[true][pred] = penalty for predicting pred when true is actual
- **Costs**: "down"→"up" and "up"→"down" = 5 (most dangerous); "steady"/"no"→wrong = 1–2
- **Evaluation**: `evaluate_model()` returns `clinical_cost` (average cost per sample)
- **Comparison**: `compare_models()` includes `clinical_cost` in output

### Impact
- **Model selection**: Can compare models by expected clinical cost instead of only F1.
- **Safety**: Penalizes dangerous misclassifications more than benign ones.
- **Usage**: `evaluation_summary.csv` now has a `clinical_cost` column; lower is better.

---

## 3. ICR/ISF Integration

### What Was Done
- **Schema**: Added `icr`, `isf` to `PatientInput`; `RecommendationConfig` has `default_icr=10`, `default_isf=50`, `target_glucose_mgdl=100`
- **Validation**: Domain validation for `icr` (1–50), `isf` (10–200)
- **Recommendation**: `_compute_meal_bolus(carbs, icr)` = carbs/ICR; `_compute_correction_dose(glucose, target, isf)` = (glucose-target)/ISF when glucose > target
- **API**: `run_recommend` passes `icr`, `isf` to `patient_dict`

### Impact
- **Recommendation**: When provided, meal bolus and correction are computed using standard clinical formulas.
- **Response**: `RecommendationResponse` includes `meal_bolus_units`, `correction_dose_units`.
- **Context**: Context summary includes "Meal bolus: X units; Correction: Y units" when applicable.

---

## 4. Separate Meal vs Correction Dose

### What Was Done
- **DosageSuggestion**: Added `meal_bolus_units`, `correction_dose_units`
- **RecommendationGenerator**: Computes both when `anticipated_carbs` > 0 and/or `glucose_level` > target
- **API**: `RecommendationResponse` includes both fields

### Impact
- **Clarity**: Clinicians see meal vs correction separately.
- **Actionability**: Aligns with pump/MDI workflows.

---

## 5. Personalized max_adjustment

### What Was Done
- **Function**: `_personalized_max_adjustment(weight_kg, base_max)` scales caps by weight (e.g., 50 kg → ~3, 90 kg → 5)
- **Usage**: `score_to_dose_change()` uses personalized max when `weight_kg` is provided

### Impact
- **Safety**: Lighter patients get smaller dose caps.
- **Relevance**: Heavier patients can receive larger adjustments when appropriate.

---

## 6. Feedback Loop for Clinician Overrides

### What Was Done
- **DB**: New table `clinician_feedback` (id, created_at, record_id, request_id, predicted_class, clinician_action, actual_dose_units, override_reason, input_summary)
- **Storage**: `insert_clinician_feedback()`, `get_clinician_feedback()`
- **API**: `POST /feedback` to record feedback; `GET /feedback` to list

### Impact
- **Learning**: Overrides can be used for retraining or analysis.
- **Audit**: Tracks when clinicians disagree with recommendations.

---

## 7. Production Monitoring

### What Was Done
- **Module**: `insulin_system.monitoring` with `PredictionMonitor`
- **Logging**: Each recommendation logs to `outputs/monitoring/prediction_stats.jsonl`
- **Stats**: `get_recent_stats(n)` returns class distribution, avg confidence, high-risk %
- **API**: `GET /monitoring/stats?n=100` for recent stats

### Impact
- **Observability**: Track prediction distribution over time.
- **Drift**: Can detect shifts in input distribution or model behavior.

---

## 8. API Changes

| Endpoint | Change |
|----------|--------|
| `POST /recommend` | Request body accepts `icr`, `isf`; response includes `meal_bolus_units`, `correction_dose_units` |
| `POST /feedback` | New: record clinician override |
| `GET /feedback` | New: list feedback records |
| `GET /monitoring/stats` | New: prediction stats |

---

## 9. Retraining Required

**Important**: The model must be retrained to include the new contextual features. Run:

```bash
python run_evaluation.py --data data/SmartSensor_DiabetesMonitoring.csv
```

On Windows, if parallel training crashes, use `--n-jobs 1`:

```bash
python run_evaluation.py --data data/SmartSensor_DiabetesMonitoring.csv --no-eda --n-jobs 1
```

Or train a single model:

```bash
python run_evaluation.py --data data/SmartSensor_DiabetesMonitoring.csv --no-eda --models logistic_regression --n-jobs 1
```

---

## 10. Testing

Run the quick integration test:

```bash
python test_improvements.py
```

Or run the full test suite:

```bash
python -m pytest tests/ -v
```
