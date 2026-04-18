# GlucoSense — How to run the system

**Workspace root:** open this folder in your editor (`Glucosense/Glucosense` — where `app.py`, `backend/`, `frontend/`, and `data/` live).

**Full detail:** [docs/RUN.md](docs/RUN.md)

---

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| Python 3.9+ | Use a venv (e.g. `.venv`); VS Code/Cursor: select that interpreter. |
| Node.js 18+ | For the React frontend. |
| Data file | `data/SmartSensor_DiabetesMonitoring.csv` (default for training). |

**Install dependencies (once):**

```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

**Windows — broken `.venv` after copying the project?**  
If `.venv` points at another PC’s Python path, run from the project root:

```powershell
.\scripts\windows\setup_venv.ps1 -Recreate
```

That creates a fresh venv and installs `requirements.txt`. The API needs **xgboost** (and related libs) installed to load `outputs/best_model/inference_bundle.joblib`.

---

## Step 1 — Train the model (required for recommendations)

From the **project root**:

```bash
python run_pipeline.py
```

**Faster try-out** (~2 min):

```bash
python run_pipeline.py --no-eda --models gradient_boosting
```

**Output:** `outputs/best_model/inference_bundle.joblib` (used by the API).

*Alternative path:* `python scripts/pipeline/run_pipeline.py` (same behavior).

---

## Step 2 — Start the API (FastAPI in `backend/`)

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
# equivalent: uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

- **API docs:** http://localhost:8000/docs  
- **Health check:** http://localhost:8000/api/health  

Keep this terminal running.

---

## Step 3 — Start the frontend (new terminal)

**Recommended (API + UI in one command — no `ECONNREFUSED`):**

```bash
cd frontend
npm install
npm start
```

This starts **FastAPI on :8000**, waits until `/api/health` responds, then starts **Vite**. Press `Ctrl+C` once to stop both.

**Or** run API and UI separately:

```bash
# Terminal 1 (repo root): uvicorn app:app --reload --host 127.0.0.1 --port 8000
# Terminal 2:
cd frontend
npm run dev
```

- **App:** http://localhost:5173 (or **5174** if 5173 is busy)  
- The dev server proxies `/api` to `http://localhost:8000`.

---

## Step 4 — Use the app

1. Open **http://localhost:5173**.  
2. **Patients** — register a patient (recommendations need a `patient_id`).  
3. **Dashboard** — enter assessment data and get a recommendation.

---

## Windows: one command (backend + frontend)

**Option A — from `frontend` (same as `npm start` above):**

```powershell
cd frontend
npm start
```

**Option B — PowerShell from repo root:**

```powershell
.\scripts\windows\run_dev.ps1
```

---

## Production-style (single port)

Build the UI, then run only the API (serves static files):

```bash
cd frontend && npm run build && cd ..
uvicorn app:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** (API remains under `/api/...`).

---

## Common problems

| Problem | What to do |
|---------|------------|
| **503 / model not loaded** | Run **Step 1** (`run_pipeline.py`). |
| **Data file not found** | Check `data/SmartSensor_DiabetesMonitoring.csv` exists. |
| **Frontend errors / ECONNREFUSED** | Start the **API first**, then the frontend, or use `run_dev.ps1`. |
| **Port 8000 in use** | Run `uvicorn ... --port 8001` and point Vite’s proxy at 8001 (see `frontend/vite.config.js`). |

---

## Optional: launcher script

```bash
python launcher.py
```

(Starts backend + frontend via `scripts/launcher.py`; requires dependencies as above.)

---

## Clinical reminder

GlucoSense is **clinical decision support**, not autonomous treatment. All outputs require **qualified clinician review**.
