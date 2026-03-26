# Clinical ML Pipeline — v2 (Experiment-Informed)

## Key Changes Based on Experiments

| Finding | Action |
|---------|--------|
| SMOTE hurts performance | **Removed** — use class_weight and cost_sensitive only |
| Class weights outperform SMOTE | **Default** imbalance strategy |
| Tree-based models best | Focus on XGBoost, LightGBM, CatBoost, RF, Extra Trees |
| LR and SVM poor | **Excluded** from default model list |
| Ensemble reduces clinical risk | **Stacking** + soft voting |
| ROC-AUC good (0.76+) | **Threshold optimization** to exploit class separation |
| Overfitting (RF 91% train vs 58% test) | **Regularization**, max_depth limits, overfitting_gap tracking |

## Phases Implemented

### Phase 1 — Pipeline Audit
- No data leakage (impute/scale fit on train only)
- Stratified random split (80/10/10)
- Stratified CV for tuning
- Modular components

### Phase 2 — Imbalance (SMOTE Removed)
- **class_weight**: Balanced weights
- **cost_sensitive**: 2× weight for minority classes (down, no)
- SMOTE, ADASYN, SMOTE+Tomek **removed**

### Phase 3 — Feature Engineering
- Correlation removal (>0.95) in FeatureSelector
- Mutual information selection
- Domain keep list

### Phase 4 — Advanced Models
- **XGBoost** (early stopping, regularization)
- **LightGBM**
- **CatBoost**
- **Random Forest**, **Extra Trees**, **Balanced Random Forest**
- **MLP** (shallow neural net)
- Optuna tuning (40 trials)

### Phase 5 — Threshold Optimization
- Cost-sensitive threshold search
- Per-class probability thresholds
- Minimizes clinical cost

### Phase 6 — Ensemble
- **Stacking** with LogisticRegression meta-learner
- **Soft voting** fallback
- Combines top 3 models by F1-weighted

### Phase 7 — Overfitting Control
- max_depth limits (RF: 5–12, GB: 3–8)
- reg_alpha, reg_lambda for boosters
- overfitting_gap tracked and used in selection

### Phase 8–11
- Experiment tracking (CSV)
- Multi-objective selection (clinical_cost → F1 → overfitting_gap)
- System update (inference_bundle.joblib)
- Evaluation report + artifacts (confusion matrix, ROC, etc.)

## How to Run

```bash
# Full pipeline (all models, threshold opt, stacking)
python run_clinical_ml_improvement.py

# Quick test
python run_clinical_ml_improvement.py --max-experiments 4 --models gradient_boosting random_forest --imbalance class_weight

# Disable threshold optimization
python run_clinical_ml_improvement.py --no-threshold-opt

# Disable stacking
python run_clinical_ml_improvement.py --no-stacking
```

## Outputs

| Path | Description |
|------|-------------|
| `outputs/best_model/` | Inference bundle (auto-used by API) |
| `outputs/clinical_ml_experiments/experiment_table.csv` | All experiments |
| `outputs/clinical_ml_experiments/final_evaluation_report.json` | Best model summary |
| `outputs/clinical_ml_experiments/best_model_artifacts/` | Confusion matrix, ROC, learning curve |

## Dependencies

- xgboost, lightgbm, catboost
- imbalanced-learn (for BalancedRandomForest)
- optuna
