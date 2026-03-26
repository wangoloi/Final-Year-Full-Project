# Insulin Prediction Pipeline Revision — File Summary

All files and modifications for the revised model development pipeline are documented below.

## New Files Created

| File | Purpose |
|------|---------|
| `notebooks/insulin_prediction_development.ipynb` | Full 11-section development notebook (EDA, preprocessing, models, SHAP, saving) |
| `run_development.py` | Standalone script that runs the revised pipeline (alternative to notebook) |
| `PIPELINE_REVISION_SUMMARY.md` | This summary document |

## Modified Files

| File | Modifications |
|------|---------------|
| `src/insulin_system/models/definitions.py` | Added `get_model_definitions(exclude_mlp=False)` to optionally omit MLP |
| `src/insulin_system/models/training.py` | Added `ModelTrainer(exclude_mlp=True)` — MLP excluded by default |
| `src/insulin_system/data_processing/split.py` | Added `RandomSplitter` for stratified train/test split |
| `src/insulin_system/config/schema.py` | Added `PipelineConfig.split_type` ("temporal" \| "random") |
| `src/insulin_system/data_processing/pipeline.py` | Uses `RandomSplitter` when `split_type="random"`; imports `RandomSplitter` |
| `run_evaluation.py` | Excludes MLP by default; added `--random-split` flag; uses `PipelineConfig` when `--random-split` |

## Split Configuration

- **80% train, 10% validation, 10% test**
- Applies to both temporal and random split modes

## Usage

### Run evaluation (default: temporal split, 80/20, no MLP)
```bash
python run_evaluation.py
```

### Run evaluation with random stratified split
```bash
python run_evaluation.py --random-split
```

### Run development pipeline (standalone script)
```bash
python run_development.py
```

### Run development notebook
Open `notebooks/insulin_prediction_development.ipynb` and run all cells.

## Workflow Sections (Notebook / run_development.py)

1. Data Loading and Understanding  
2. Data Cleaning and Preprocessing (drop patient_id, handle missing, outliers, label encoding)  
3. Insightful Data Visualization (feature vs Insulin, correlation, class balance)  
4. Correlation Analysis (target correlations, multicollinearity)  
5. Feature Engineering and Feature Selection (clinical features, mutual information)  
6. Model Training Pipeline (train/test split, StandardScaler, models excluding MLP)  
7. Model Evaluation (confusion matrix, classification report, F1-weighted)  
8. SHAP Explainability Integration (TreeExplainer / KernelExplainer)  
9. Custom Prediction Testing (new patient input with SHAP explanation)  
10. Model Saving and Deployment (bundle, scaler, encoders, metadata)  
11. Clinical Safety Considerations (disclaimer)

## Clinical Disclaimer

The API responses already include `clinical_disclaimer` in `src/insulin_system/api/schemas.py`. All prediction, explain, and recommend endpoints return this disclaimer.
