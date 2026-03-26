# Glucosense ML Pipeline — Improvements Summary

## Executive Summary

This document summarizes the comprehensive refactoring and improvements applied to the Glucosense machine learning pipeline for multi-class glucose trend prediction. The system predicts insulin adjustment classes: **down**, **no**, **steady**, **up**.

**Baseline**: F1-weighted ~0.37 (gradient_boosting)  
**Improvements target**: Higher F1 through feature engineering, class balancing, stacking, and evaluation enhancements.

---

## Step 1 — System Analysis (Findings)

### Identified Bottlenecks

1. **Severe Class Imbalance**
   - steady: 53%, up: 34%, no: 7%, down: 6%
   - Models biased toward majority classes (steady, up)
   - Minority recall good but precision very low (down: 18%, no: 17%)

2. **Limited Feature Set**
   - No glucose zone numeric encoding
   - Missing IOB × anticipated_carbs interaction (relevant for meal dosing)
   - Feature selection K=30 may drop useful signals

3. **Hyperparameter Search**
   - Random search limited to 30 iterations
   - No stacking/ensemble beyond single models

4. **Class Weighting**
   - minority_class_weight_multiplier=2.0; minority classes (down, no) under-weighted

5. **Evaluation Gaps**
   - No model comparison visualization
   - Classification report not persisted in metrics

---

## Step 2 — Data and Feature Improvements

### Implemented

| Improvement | Description | Expected Impact |
|-------------|-------------|-----------------|
| **glucose_zone_numeric** | Numeric encoding (0–5) of glucose zones: hypo, low-normal, target, mild/moderate/severe hyper | Better trend signal for model |
| **iob × anticipated_carbs** | Interaction for meal dosing context | Improved meal-bolus predictions |
| **SELECTION_K** | Increased from 30 to 35 | Retain more informative features |
| **DOMAIN_KEEP** | Added glucose_zone_numeric | Ensures zone feature survives selection |

### Class Imbalance

- **minority_class_weight_multiplier**: 2.0 → 2.5
- **minority_classes**: `("down", "no")` — sample weights boosted for XGBoost, class_weight for sklearn

---

## Step 3 — Model Improvements

### Stacking Ensemble

- **New model**: `stacking_ensemble`
- **Base estimators**: Random Forest + Gradient Boosting (XGBoost) + Logistic Regression
- **Meta-learner**: Logistic Regression with CV=3
- **Grid**: `final_estimator__C`: [0.1, 1.0, 10.0]

### Hyperparameter Tuning

- **random_search_n_iter**: 30 → 50
- Label encoding for StackingClassifier when it contains XGBoost

---

## Step 4 — Code Refactoring

### New `ml/` Package

```
src/ml/
├── config.py           # MLPipelineConfig, DataConfig, TuningConfig, etc.
├── data_loader.py      # DataLoader, load_dataset
├── preprocessing.py    # Preprocessor (impute, outlier, encode, scale, split)
├── feature_engineering.py  # EnhancedFeatureEngineer, FeatureSelectorRFE
├── hyperparameter_tuning.py  # tune_model, Optuna support
├── evaluation.py       # EvaluationResult, classification report, CV
├── visualization.py    # plot_confusion_matrix, plot_roc_curves, etc.
└── __init__.py
```

### Modified Existing Code

- **schema.py**: INTERACTION_PAIRS, SELECTION_K, DOMAIN_KEEP, ModelConfig (n_iter, multiplier)
- **feature_engineering.py**: glucose_zone_numeric, DERIVED_NUMERIC_BASE
- **definitions.py**: StackingClassifier, include_stacking
- **training.py**: include_stacking, _needs_label_encoding for Stacking
- **evaluation.py**: classification_report, precision_recall_fscore_support
- **evaluation_framework.py**: Model comparison plot, improved CM/ROC styling

### New Entry Point

- **run_improved_evaluation.py**: Runs enhanced pipeline with stacking and improved config.

---

## Step 5 — Evaluation Improvements

### Metrics Persisted

- Accuracy, precision/recall/F1 (macro + weighted)
- ROC-AUC (One-vs-Rest weighted)
- Confusion matrix
- **Per-class**: precision, recall, F1
- **Classification report**: Full sklearn `classification_report` string in `metrics.json`
- Clinical cost (from cost matrix)

### Metric Definitions

| Metric | Meaning |
|--------|---------|
| **F1-weighted** | F1 averaged by class support; reflects performance on imbalanced data |
| **F1-macro** | Unweighted average of per-class F1; treats all classes equally |
| **ROC-AUC OvR** | One-vs-Rest AUC; discriminative ability per class |
| **Clinical cost** | Penalty for misclassifications (e.g. down→up worse than steady→no) |

---

## Step 6 — Visualization Improvements

### Changes

- **Confusion matrix**: Larger figure, bold title, cbar label
- **ROC curves**: Linewidth=2, grid, improved legend
- **Model comparison**: New `model_comparison.png` — bar chart of f1_weighted, accuracy, roc_auc_weighted
- **General**: DPI 120→150, `bbox_inches="tight"`

---

## Step 7 — Performance Optimization Summary

| Technique | Applied | Expected Impact |
|-----------|---------|-----------------|
| Feature engineering | glucose_zone_numeric, iob×carbs | +1–3% F1 |
| Class balancing | multiplier 2.5, minority classes | Better recall on down/no |
| Feature selection | K=35, domain keep | Fewer dropped signals |
| Stacking | RF+GB+LR meta | +2–5% vs best single model |
| Hyperparameter tuning | 50 iterations | Better model fit |

---

## Step 8 — Final Outputs

### Artifacts

- `outputs/evaluation/<model>/`: metrics.json, confusion_matrix.png, roc_ovr.png, learning_curve.png, feature importance
- `outputs/evaluation/evaluation_summary.csv`: Ranked by f1_weighted
- `outputs/evaluation/model_comparison.png`: Bar chart across models
- `outputs/best_model/`: inference_bundle.joblib, metadata.json

### How to Run

```bash
# Full clinical ML improvement pipeline (calibration, multi-objective selection)
python run_clinical_ml_improvement.py

# Deploy best model from existing experiment table (no re-training of all models)
python scripts/deploy_best_from_experiments.py

# Full improved pipeline (with stacking)
python run_improved_evaluation.py

# Without stacking
python run_improved_evaluation.py --no-stacking

# Original pipeline (unchanged)
python run_evaluation.py
```

### Model Selection (Rank-Based)

Model selection uses **Borda-style rank-based scoring** (no arbitrary weights):

- For each metric, rank models: 1=best, 2=second, …, N=worst
- Higher is better: F1_weighted, ROC_AUC, F1_macro
- Lower is better: clinical_cost, overfitting_gap
- Sum ranks across all 5 metrics; pick model with **lowest total rank**

**Recommended production model**: Gradient Boosting + Sigmoid calibration (class_weight).

### Training Improvements (Safety & Performance)

1. **Safety constraints** – Models must pass `f1_macro >= 0.35` and `clinical_cost <= 0.8` to be eligible for selection.
2. **Cost-sensitive sample weights** – Weights derived from clinical cost matrix (higher weight for classes with costly misclassifications).
3. **Patient-based split** – Use `--patient-split` so each patient appears in only one split (no leakage).
4. **Optuna trials** – Increased from 40 to 80 for better hyperparameter search.
5. **Temperature scaling** – Added as calibration option (sklearn 1.8+); falls back to sigmoid on older versions.

---

## Future Improvements

1. **Deep Learning**
   - LSTM/Transformer for temporal sequences if patient-level time series available
   - Attention over glucose history for trend modeling

2. **Advanced Feature Engineering**
   - Rolling stats: mean, std, slope of glucose over last N readings
   - Time-of-day encoding (meal times, overnight)
   - CGM-derived: MARD, time-in-range proxy

3. **Class Imbalance**
   - SMOTE-Tomek combined
   - Focal loss for XGBoost
   - Threshold tuning per class (instead of 0.5)

4. **Hyperparameter Tuning**
   - Optuna for all models
   - Bayesian optimization

5. **Calibration**
   - Platt (sigmoid) and isotonic calibration implemented
   - Calibration applied before threshold optimization

6. **Data**
   - Temporal split validation (if patient_id reflects time)
   - Cross-validation by patient (leave-patient-out)

---

## Reproducibility

- `random_state=42` used across pipeline
- All configs centralized in `schema.py` and `ml/config.py`
- No data leakage: imputation, scaling, feature selection fitted on train only
- Temporal split by default; `--random-split` for stratified random

