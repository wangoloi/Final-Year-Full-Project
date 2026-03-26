# GlucoSense System Summary

## Best Model in Use

**Model:** `gradient_boosting` (XGBoost)  
**Selection metric:** `f1_weighted` (weighted F1 score across insulin categories: down, up, steady, no)  
**Current performance:** ~60% f1_weighted (from `outputs/best_model/metadata.json`)

The pipeline selects the best model by comparing all trained models on the test set and choosing the one with the highest f1_weighted. The selected model is saved to `outputs/best_model/inference_bundle.joblib` and used by:
- The API (`/api/recommend`, `/api/predict`, `/api/explain`)
- The frontend Dashboard (Get recommendation)
- The Model Info page (sidebar → Model Info)

## How to Run the Full System

### 1. Pipeline (train/save best model)
```bash
python run_pipeline.py --no-eda --models gradient_boosting random_forest
```
Or full pipeline: `python run_pipeline.py`

### 2. Recommendation engine (standalone)
```bash
python run_recommendation.py --patients 5
```

### 3. Backend API
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

### 4. Frontend
```bash
cd frontend && npm run dev
```
Open http://localhost:5173

## Key Components

| Component | Path | Purpose |
|-----------|------|---------|
| Pipeline | `run_pipeline.py` → `run_evaluation.py` | Data processing, model training, best model selection |
| Recommendation | `run_recommendation.py` | Batch recommendations with explanations |
| API | `app.py`, `src/insulin_system/api/` | REST endpoints for prediction, explain, recommend |
| Frontend | `frontend/` | React clinician UI |
| Model bundle | `outputs/best_model/` | Saved model + preprocessors for inference |

## Error Handling

- **Model not loaded (503):** Run `python run_pipeline.py` first.
- **Corrupted model file:** Re-run the pipeline to regenerate.
- **Sklearn version mismatch:** Warnings are suppressed; model should still load.
