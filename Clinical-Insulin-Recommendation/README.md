# GlucoSense Clinical Support

**Type 1 Diabetes Management** – Insulin dosage prediction, recommendation, and explainability as a clinical decision support system.

---

## Clinical safety notice

- **This system is a clinical decision support tool, not an autonomous diagnostic system.**
- **All recommendations must be reviewed by a qualified healthcare professional.**
- The system should **not** be used as the sole basis for treatment decisions.
- Regular validation against clinical outcomes is required.
- Model performance should be monitored continuously in production.

---

## Overview

GlucoSense integrates:

1. **Prediction** – Model inference from patient features (glucose, HbA1c, BMI, etc.) to insulin category (down / up / steady / no).
2. **Recommendation** – Clinical dosage suggestions with magnitude, confidence, and high-risk flagging.
3. **Explainability** – SHAP-based drivers and counterfactual scenarios.

The **backend** is the FastAPI engine in **`backend/`** (saved model + preprocessing, recommendation generator, explainability). The **frontend** is the React (Vite) web UI in **`frontend/`**.

**Layout:** see **[docs/STRUCTURE.md](docs/STRUCTURE.md)**.

---

## Requirements

- Python 3.9+
- See `requirements.txt` (pandas, numpy, scikit-learn, xgboost, shap, fastapi, uvicorn, pydantic, joblib, etc.).

---

## Quick start

### 1. Train and save the best model

```bash
pip install -r requirements.txt
python run_evaluation.py
# or: python scripts/pipeline/run_evaluation.py
# Default training CSV: data/SmartSensor_DiabetesMonitoring.csv (override with --data path/to/file.csv)
```

This saves the best model (by F1-weighted) to `outputs/best_model/`.

**Smart Sensor dataset pipeline (Prompt spec):** trains tabular + optional LSTM models on `data/SmartSensor_DiabetesMonitoring.csv`, writes metrics, plots, `model_bundle/`, and **`outputs/smart_sensor_ml/Smart_Sensor_ML_Report.pdf`**.

```bash
python scripts/run_smart_sensor_ml.py --skip-lstm   # add TensorFlow and omit --skip-lstm for LSTM
```

### 2. Run the API (FastAPI backend)

From the **repository root**:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
# or explicitly:
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

- **POST /api/predict** – Get insulin prediction (JSON body: patient fields).
- **POST /api/explain** – Get explanation for a prediction.
- **POST /api/recommend** – Get full recommendation with reasoning.
- **GET /api/model-info** – Model metadata and performance.
- **GET /api/feature-importance** – Global feature importance.

API docs: http://localhost:8000/docs

### 3. Run the frontend (clinician UI)

```bash
cd frontend && npm install && npm start
```

Open http://localhost:5173. Use **Dashboard** to enter patient data and get a recommendation; **Records** to view stored prediction records (SQLite); **Model info** to view the current model.

**Run guide:** **[HOW_TO_RUN.md](HOW_TO_RUN.md)** (quick steps) · **[docs/RUN.md](docs/RUN.md)** (full detail + troubleshooting).

### 4. Production build (frontend + API)

```bash
cd frontend && npm run build
# Then run API; it serves the built frontend at /
uvicorn app:app --host 0.0.0.0 --port 8000
```

---

## Project structure (high level)

| Location | Purpose |
|----------|---------|
| **`app.py`** | FastAPI entrypoint (API + optional static SPA). |
| **`data/`** | Datasets (default: `SmartSensor_DiabetesMonitoring.csv`). |
| **`docs/`** | Documentation — **`ARCHITECTURE.md`**, **`RUN.md`**, guides, notes. |
| **Integrated workspace** | From workspace root: **`../../SYSTEM_PIPELINE.md`**, **`../../ARCHITECTURE.md`** (GlucoSense + Meal Plan + ML flows). |
| **`frontend/`** | React (Vite) clinician UI. |
| **`scripts/pipeline/`** | ML / evaluation entrypoints (`run_evaluation.py`, `run_pipeline.py`, …). |
| **`scripts/notebook/`** | Execute development notebook end-to-end (`execute_development_notebook.py`). |
| **`scripts/windows/`** | PowerShell/Batch helpers (`run_dev.ps1`, `run_all.ps1`, …). |
| **`scripts/`** | Other utilities (`launcher.py`, deploy, cost-sensitive eval, …). |
| **`src/insulin_system/`** | Core logic: API, data_processing, models, persistence, explainability, recommendation, safety, storage. |
| **`backend/`** | Alternate FastAPI app (cohort dashboard API); main UI uses `app.py`. |
| **`tests/`** | Pytest; integration checks under `tests/integration/`. |
| **`run_evaluation.py`**, **`run_pipeline.py`**, **`launcher.py`** (repo root) | Thin shims that forward to `scripts/` (optional convenience). |
| **`requirements/`** | Extra dependency lists (e.g. `dashboard.txt` for Streamlit dashboard). |

---

## Input validation

- Patient input is validated via Pydantic (`PatientInput`). Missing optional fields may be imputed by the pipeline.
- Invalid or missing required structure returns 400 with a clear error message.

---

## Audit and safety

- **Database**: Prediction and recommendation records are stored in SQLite at `outputs/glucosense.db`; the UI **Records** page and **GET /api/records** list them.
- **Audit log**: Every prediction and recommendation is also logged to `outputs/audit/predictions.jsonl` (timestamp, endpoint, predicted_class, confidence, is_high_risk).
- **High-risk flag**: Low confidence or high uncertainty triggers a flag for clinician review in the response and UI.
- **Disclaimer**: Every API response includes the clinical disclaimer; the frontend displays it with the recommendation.

---

## Limitations

- Model performance depends on training data and may not generalize to all populations.
- Bias and fairness should be evaluated per deployment (e.g. across demographic groups if available).
- Out-of-distribution inputs may produce unreliable predictions; confidence and uncertainty are provided to support review.

---

## License and use

For use in clinical or research settings, ensure compliance with local regulations and institutional review. All treatment decisions remain the responsibility of qualified healthcare professionals.
