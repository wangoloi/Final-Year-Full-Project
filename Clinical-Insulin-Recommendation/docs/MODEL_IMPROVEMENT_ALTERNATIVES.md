# Model Improvement Alternatives

## Cost-Sensitive Learning (Applied)

**Status: Applied** – 2× weight for minority classes ("down", "no").

| Model | Metric | Baseline | Cost-Sensitive |
|-------|--------|----------|----------------|
| Logistic Regression | down recall | 0.48 | **0.74** (+55%) |
| Logistic Regression | no recall | 0.62 | **0.81** (+31%) |
| Logistic Regression | f1_weighted | 0.46 | 0.36 (trade-off) |

Trade-off: improved minority class capture at the cost of overall f1_weighted. Preferable for clinical safety (reducing missed "reduce insulin" recommendations).

---

## Summary of Step 8 Evaluation

The Step 8 improvements (calibration, extra domain features, tighter regularization) were **not applied** because they caused:

| Issue | Evidence |
|-------|----------|
| **Class collapse (bias)** | Logistic regression predicted only "steady" and "up"; recall for "down" and "no" dropped to 0 |
| **Overfitting** | Random forest: train F1 0.88 vs test F1 0.60 |
| **Worse macro F1** | Improved logistic: f1_macro 0.287 vs baseline 0.374 |
| **Minority class loss** | Random forest improved: "no" recall 0.07 → 0 (complete loss) |

**Reverted changes:**
- `use_calibration = False` (was causing class collapse)
- Removed `glucose_zone_ordinal`, `glucose_hba1c_ratio`, `activity_insulin_ratio` from feature engineering

---

## Alternative Approaches to Improve Without Overfitting or Bias

### 1. **Per-class threshold tuning**
Instead of calibration, tune decision thresholds per class to improve recall on minority classes.

- Use `predict_proba` and set class-specific thresholds (e.g., lower threshold for "down"/"no" to increase recall)
- Optimize thresholds on validation set using `f1_macro` or a custom metric that penalizes missing minority classes

### 2. **Cost-sensitive learning (stronger class weights)**
- Use `class_weight` with custom weights (e.g., `{0: 3, 1: 3, 2: 1, 3: 1}`) to upweight minority classes
- Or use `sample_weight` from `compute_sample_weight("balanced", y)` with a multiplier for minority classes

### 3. **SMOTE for non-XGBoost models only**
- Apply SMOTE in the pipeline only for models that support it (logistic, DT, RF, SVM, MLP)
- For XGBoost, keep `class_weight` (SMOTE + XGBoost sample_weight causes size mismatch)
- Implement model-specific preprocessing branches in the training pipeline

### 4. **Ensemble with diversity**
- Train multiple models and ensemble predictions (voting or stacking)
- Ensure ensemble includes models that capture different classes (e.g., baseline logistic captures "down"/"no" better than improved)
- Use `VotingClassifier` with `voting="soft"` and tune weights per class

### 5. **Two-stage or hierarchical classification**
- Stage 1: Binary "needs change" (down/no/up) vs "steady"
- Stage 2: Among "needs change", classify down vs no vs up
- Reduces imbalance in each stage and can improve minority class recall

### 6. **Focal loss or custom loss (for MLP/RNN)**
- Use focal loss to downweight easy majority-class examples and focus on hard/minority examples
- Requires custom training loop for MLP/RNN

### 7. **Feature selection focused on minority classes**
- Run feature importance analysis per class (e.g., permutation importance per class)
- Retain features that help "down" and "no" even if they hurt overall accuracy slightly

### 8. **Data augmentation for minority classes**
- Oversample minority classes with small random perturbations (e.g., add Gaussian noise to numeric features)
- More conservative than SMOTE; less risk of synthetic samples hurting generalization

---

## Recommended Next Steps

1. ~~**Quick win:** Try **cost-sensitive learning**~~ → **Applied** (2× for down/no).
2. **Medium effort:** Implement **per-class threshold tuning** on validation set.
3. **Higher effort:** Explore **two-stage classification** if clinical workflow allows.

Run `python run_evaluation.py` to regenerate evaluation with cost-sensitive learning.
