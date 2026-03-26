# GlucoSense — How to Run

This guide explains how to run the GlucoSense pipeline, API, and frontend. For **Meal Plan + integrated ports + Smart Sensor ML**, see the workspace **[SYSTEM_PIPELINE.md](../../../SYSTEM_PIPELINE.md)** and root **[README.md](../../../README.md)**.

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

## 1. Run the Full ML Pipeline

Train models and save the best one for inference:

```bash
python run_pipeline.py
# or: python scripts/pipeline/run_pipeline.py
```

**Note:** Full pipeline takes ~5–10 minutes (all models). For quick testing, use:
`python run_pipeline.py --no-eda --models gradient_boosting` (~2 min).

Options:

- `--data PATH` — Path to CSV (default: `data/SmartSensor_DiabetesMonitoring.csv`)
- `--no-eda` — Skip EDA plots
- `--models NAME1 NAME2` — Train only specific models (e.g. `gradient_boosting random_forest`)
- `--out-dir DIR` — Evaluation output (default: `outputs/evaluation`)
- `--best-model-dir DIR` — Where to save the best model (default: `outputs/best_model`)
- `--random-split` — Use random stratified split instead of temporal

Output:

- `outputs/best_model/inference_bundle.joblib` — Model used by the API
- `outputs/evaluation/` — Metrics, confusion matrices, ROC curves, etc.

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
| `No saved model found at outputs/best_model/inference_bundle.joblib` | Run `python run_pipeline.py` first |
| `Data file not found` | Ensure `data/SmartSensor_DiabetesMonitoring.csv` exists |
| Frontend can't reach API | Start backend first, then frontend. Or use `.\scripts\windows\run_dev.ps1` for correct order. |
| `ECONNREFUSED` proxy errors | Backend wasn't ready when frontend started. Use `scripts\windows\run_dev.ps1` or start backend first. |
| Port 8000 in use | Use `--port 8001` and update frontend proxy if needed |

---

## Alternative Scripts

- `run_evaluation.py` — Same as `run_pipeline.py` (full evaluation + save best model)
- `run_development.py` — Standalone development pipeline (different bundle format; not used by API)

---

## 6. System Interaction Test (CDS & User Support)

After starting the API, run scenarios to validate CDS Safety Engine and user/design-group support:

```bash
python scripts/test_system_interaction.py --base-url http://localhost:8000
```

Tests: hypo rejection, CGM error handling, high ketones, target range, ICR/ISF meal+correction.
