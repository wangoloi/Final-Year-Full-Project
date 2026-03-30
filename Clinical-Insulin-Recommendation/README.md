# GlucoSense Clinical Support

**Type 1 diabetes management** — insulin guidance, recommendations, and clinical decision support (CDS).

---

## Clinical safety notice

- This system is **clinical decision support**, not autonomous diagnosis.
- All recommendations must be reviewed by a **qualified healthcare professional**.
- Do not use as the sole basis for treatment decisions.

---

## Overview

GlucoSense combines:

1. **Prediction / recommendation** — FastAPI backend with validated patient input and structured responses.
2. **Web UI** — React (Vite) clinician app in **`frontend/`**.
3. **Offline training** — **`clinical_insulin_pipeline`** (insulin dose regression, 0–10 IU) under **`backend/src/clinical_insulin_pipeline/`**, run from the repo root via **`run_clinical_insulin_pipeline.py`**.

**Layout:** **[docs/STRUCTURE.md](docs/STRUCTURE.md)**.

---

## Requirements

- Python 3.9+
- Node.js 18+ (frontend)
- Dependencies: **`requirements.txt`**

---

## Quick start

### 1. Install

```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### 2. Train the clinical insulin pipeline (optional)

From the **Clinical-Insulin-Recommendation** root:

```bash
python run_clinical_insulin_pipeline.py
```

Faster smoke (skips heavy plots):

```bash
python run_clinical_insulin_pipeline.py --skip-learning-curve --skip-shap
```

Writes artifacts under **`outputs/clinical_insulin_pipeline/latest/`**. The API may still use a separate bundle under **`outputs/best_model/`** depending on deployment; see **`outputs/README.md`**.

### 3. Run the API

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000/docs** for OpenAPI.

### 4. Run the frontend

```bash
cd frontend
npm start
```

Starts the API on **:8000** (if configured in `package.json`), then Vite. Or run **`npm run dev`** with the API already running.

**More detail:** **[HOW_TO_RUN.md](HOW_TO_RUN.md)** · **[docs/RUN.md](docs/RUN.md)**.

---

## Project structure (high level)

| Location | Purpose |
|----------|---------|
| **`app.py`** | Shim: `uvicorn app:app` from repo root. |
| **`backend/app.py`** | FastAPI application. |
| **`backend/src/insulin_system/`** | API, storage, recommendations, safety. |
| **`backend/src/clinical_insulin_pipeline/`** | Training / evaluation CLI for dose regression. |
| **`frontend/`** | React SPA. |
| **`data/`** | Datasets (e.g. `SmartSensor_DiabetesMonitoring.csv`). |
| **`outputs/`** | Models, audit, monitoring DB — see **`outputs/README.md`**. |
| **`config/`** | Clinical JSON thresholds / guidelines. |
| **`scripts/`** | Launchers, pipeline entry, Windows helpers — **`scripts/README.md`**. |
| **`tests/`** | Pytest. |
| **`docs/`** | Documentation index — **`docs/README.md`**. |

---

## Audit and safety

- Operational data and records: SQLite (default under **`outputs/`**; see runbook).
- Audit log: **`outputs/audit/`** (JSONL).
- Responses include clinical disclaimers; treat high-risk flags as requiring review.

---

## License and use

For clinical or research use, comply with local regulations and institutional review. Treatment decisions remain the responsibility of qualified healthcare professionals.
