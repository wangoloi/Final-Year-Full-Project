# GlucoSense — How to Run

This guide explains how to run the GlucoSense **clinical insulin training** pipeline, API, and frontend. For **Meal Plan + integrated ports**, see the workspace **[SYSTEM_PIPELINE.md](../../../SYSTEM_PIPELINE.md)** and root **[README.md](../../../README.md)**.

## Prerequisites

- Python 3.9+
- Node.js 18+ (for frontend)
- Data file: `data/SmartSensor_DiabetesMonitoring.csv` (or pass `--data` to pipeline scripts)

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..
```

---

## 1. Run the clinical insulin training pipeline

Train the **dose regression** pipeline (0–10 IU) and write artifacts under **`outputs/clinical_insulin_pipeline/latest/`**:

```bash
python run_clinical_insulin_pipeline.py
# delegates to: scripts/pipeline/run_clinical_insulin_pipeline.py
```

**Faster try-out** (skips learning-curve and SHAP):

```bash
python run_clinical_insulin_pipeline.py --skip-learning-curve --skip-shap
```

Common options (see `python run_clinical_insulin_pipeline.py --help`):

- `--data PATH` — CSV path (default: `data/SmartSensor_DiabetesMonitoring.csv`)
- `--out-dir` — Under `outputs/clinical_insulin_pipeline/` (default run uses `latest/`)

**Output:** leaderboard CSV, `insulin_regression_bundle.joblib`, plots, `run_metadata.json`. The FastAPI app may load a **separate** legacy bundle from **`outputs/best_model/`** when present; see **`outputs/README.md`**.

---

## 2. Run the API (Backend)

Start the FastAPI server (recommend, dose, patient-context, glucose-trends, etc.):

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

- API docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

The API loads the model from `outputs/best_model/` on first request (or at startup in background).

---

## 3. Run the Frontend

**Easiest (API + frontend — avoids proxy `ECONNREFUSED`):**

```bash
cd frontend
npm start
```

Starts uvicorn on **:8000**, waits for `/api/health`, then Vite. Use **`npm run dev`** only if the API is already running in another terminal.

- Frontend: http://localhost:5173 (or 5174 if 5173 is in use)
- Proxies `/api` and `/static` to `http://localhost:8000`

---

## 4. Run Everything (Quick Start)

**Option A – Single script (recommended, avoids proxy errors):**

```powershell
.\scripts\windows\run_dev.ps1
```

This starts the backend first, waits for it to be healthy, then starts the frontend.

**Option B – Manual (two terminals):**

```bash
# Terminal 1: API (start first, wait for "Application startup complete")
uvicorn app:app --reload --host 127.0.0.1 --port 8000

# Terminal 2: Frontend (start after backend is ready)
cd frontend && npm run dev
```

Then open http://localhost:5173 in your browser.

---

## 5. Production Build (Optional)

Serve the built frontend from the API:

```bash
cd frontend
npm run build
cd ..
uvicorn app:app --host 0.0.0.0 --port 8000
```

The API will serve the static frontend from `frontend/dist` at `/`.

---

## Configuration (JSON)

Clinical thresholds and Uganda T1D guidelines are stored in JSON:

- `config/clinical_thresholds.json` — glucose zones, ICR/ISF bounds, CDS safety, etc.
- `config/uganda_t1d_guidelines.json` — daily dose range (0.6–1.5 IU/kg), regimens, insulin types

Edit these files to change thresholds without code changes. See `docs/UGANDA_T1D_GUIDELINES.md` for details.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `No saved model found at outputs/best_model/inference_bundle.joblib` | Add a compatible `inference_bundle.joblib` under `outputs/best_model/`, or expect stub/503 on ML-heavy routes until wired |
| `Data file not found` | Ensure `data/SmartSensor_DiabetesMonitoring.csv` exists |
| Frontend can't reach API | Start backend first, then frontend. Or use `.\scripts\windows\run_dev.ps1` for correct order. |
| `ECONNREFUSED` proxy errors | Backend wasn't ready when frontend started. Use `scripts\windows\run_dev.ps1` or start backend first. |
| Port 8000 in use | Use `--port 8001` and update frontend proxy if needed |

---

## Alternative scripts

- **`scripts/dev/quick_clinical_check.py`** — Quick RF smoke test on the default CSV.
- **`pytest`** — From repo root: `pytest tests/` (includes `test_clinical_insulin_pipeline.py` smoke).
