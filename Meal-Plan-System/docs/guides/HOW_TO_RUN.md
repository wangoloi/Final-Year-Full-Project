# Glocusense (Meal Plan) — How to run

**Project root:** `Meal-Plan-System` (parent of `backend/`, `frontend/`, `scripts/`).

All **Python API** code lives under **`backend/`** (`backend/api/`, `backend/run.py`, `backend/requirements.txt`).

---

## Windows: folder path contains `;` (e.g. `year3;2 project`)

Python **cannot** create `venv` there (`;` is the PATH separator). Use the included **SUBST** helper:

```powershell
cd "E:\Glucosense app\Meal-Plan-System"
powershell -ExecutionPolicy Bypass -File .\scripts\windows\setup_venv_subst.ps1
```

- Maps **`G:`** (change with `-DriveLetter Z`) to this folder, creates **`.venv`**, installs **`backend\requirements.txt`**.
- After that, work from the virtual drive so activation works:

```powershell
G:
.\.venv\Scripts\Activate.ps1
python backend\run.py
```

Or run the API without activating:

```powershell
.\scripts\windows\run_api_subst.ps1
```

**Remove the drive mapping:** `subst G: /d` (use the letter you chose).

---

## 1. Python API (FastAPI)

From **repo root**:

```bash
pip install -r requirements.txt    # or: pip install -r backend/requirements.txt
python backend/run.py
```

Shortcut (same effect): **`python run.py`** — root shim delegates to `backend/run.py`.

- Default: **http://127.0.0.1:8000**
- Docs: **http://127.0.0.1:8000/docs**
- Meal Plan health: **GET /api/health**

Change port: `$env:PORT=9000; python backend/run.py` (PowerShell).

## 2. React frontend (Vite)

```bash
cd frontend
npm install
npm run dev
```

- Default: **http://localhost:5173** (proxies `/api` → `http://127.0.0.1:8000`)

If your project path contains `;`, npm scripts use `node ./node_modules/vite/bin/vite.js` so Vite is found on Windows.

## 3. Windows — both at once

From project root:

```powershell
# Terminal 1
python backend\run.py

# Terminal 2
cd frontend; npm run dev
```

Or **`.\scripts\start_full_system.ps1`** (opens two windows).

## Tests

From **repo root** (pytest settings in **`pyproject.toml`** — `pythonpath` / `testpaths` for `backend/`):

```bash
pip install -r requirements.txt
pytest -q
```

## Register returns 500?

1. **Confirm Meal Plan is on port 8000** — open `http://localhost:5173/api/health` — expect `"app":"glocusense-meal-plan"`.
2. **Stale SQLite schema** — delete `%LocalAppData%\Glocusense\glocusense.db` and restart the API.
3. Check the **terminal running the API** for a Python traceback.

## “Request timed out” in the browser

1. From repo root run: **`python backend\run.py`** (or **`python run.py`**).
2. Wait until **Uvicorn** is running.
3. Open **http://127.0.0.1:8000/api/health** in the browser.
4. **`.\scripts\windows\check_api_health.ps1`** — quick check from PowerShell.

**Port in use:** `$env:PORT=8001; python backend\run.py` and point Vite’s proxy at `http://127.0.0.1:8001`.
