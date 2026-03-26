# Phase 1 — Pipeline Audit Report

## 1. Pipeline Analysis

### Preprocessing
- **Imputation**: Median (numeric), mode (categorical) — fitted on train only ✓
- **Outliers**: Clip to clinical bounds — no data leakage ✓
- **Encoding**: OneHotEncoder drop_first — fitted on train ✓
- **Scaling**: StandardScaler — fitted on train ✓

### Feature Engineering
- Interactions: glucose×insulin_sensitivity, HbA1c×glucose, BMI×physical_activity, etc.
- Polynomial: glucose², HbA1c², BMI², insulin_sensitivity²
- **Potential issue**: Polynomial terms may correlate highly with base features
- **Missing**: No correlation-based feature removal

### Train/Test Split
- Temporal split by patient_id (80/10/10) or random stratified
- **Issue**: Temporal split may not stratify classes in val/test
- **Issue**: patient_id sort order may not reflect true temporal order

### Validation Strategy
- StratifiedKFold CV for hyperparameter search ✓
- **Issue**: No explicit overfitting detection (train vs val gap)

### Model Training
- RandomizedSearchCV, 50 iterations
- **Issue**: RF max_depth up to 15 — allows deep trees → overfitting
- **Issue**: No early stopping for XGBoost

### Evaluation Metrics
- F1-weighted, ROC-AUC, clinical cost ✓
- **Missing**: Macro F1 in model selection
- **Missing**: Overfitting gap tracking

## 2. Identified Weaknesses

| Weakness | Severity | Component |
|----------|----------|-----------|
| Feature redundancy (polynomial + base) | Medium | Feature engineering |
| No correlation removal | Medium | Feature selection |
| RF overfitting (91% train vs 58% test) | High | Model config |
| No early stopping (XGBoost) | Medium | Model config |
| Thresholds fixed at 0.5 | High | Prediction |
| SMOTE not tested | Medium | Imbalance |
| No Balanced Random Forest | Low | Model variety |
| No Extra Trees | Low | Model variety |

## 3. Why Performance is Low

1. **Class imbalance**: Steady (53%) and Up (34%) dominate; models bias toward majority
2. **Overfitting**: RF fits training data too well; poor generalization
3. **Suboptimal thresholds**: Default 0.5 may not minimize clinical cost
4. **Feature noise**: Correlated/redundant features add noise
5. **Limited imbalance strategies**: Only class_weight used; SMOTE/ADASYN untested

## 4. Components to Redesign

- **Feature selection**: Add correlation filter, permutation importance, RFE
- **Model config**: Add max_depth limits, early stopping, BalancedRF, ExtraTrees
- **Imbalance**: Test SMOTE, SMOTE+Tomek, ADASYN
- **Threshold**: Implement cost-sensitive threshold optimization
- **Experiment loop**: Track overfitting_gap, auto-select best by clinical_cost + F1
