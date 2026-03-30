# Repository structure

Root = `Meal-Plan-System` (this folder).

## Layout (neat separation)

| Area | Path | Purpose |
|------|------|---------|
| **Backend (FastAPI)** | **`backend/`** | All server-side code & API tests — see below |
| **Frontend (React)** | **`frontend/`** | Vite SPA (`npm run dev`) — **only client** |
| **ML / research (optional)** | **`ml-services/`**, **`models/`** | Not imported by the live API — see **`models/README.md`** (`scripts/`, `notebooks/`, `output/`) |
| **Automation** | **`scripts/`** | Cross-platform helpers (PowerShell); **Python seeds** live under **`backend/scripts/`** |
| **Docs** | **`docs/`** | Architecture, guides, reference (e.g. **`docs/guides/CHATBOT.md`**, **`TYPESENSE.md`**) |
| **Container images** | **`docker/`** | `Dockerfile.api`, `Dockerfile.web`, `nginx-meal.conf` (build context = repo root) |

## `backend/` — everything for the FastAPI service

| Path | Purpose |
|------|---------|
| **`backend/run.py`** | Uvicorn entry: `api.main:app` |
| **`backend/requirements.txt`** | Python dependencies (canonical) |
| **`backend/api/`** | FastAPI app: `main.py`, `models.py`, `core/`, `shared/`, `modules/*`, `utils/seed.py` |
| **`backend/tests/`** | `pytest` — run from repo root: `pytest` (config in **`pyproject.toml`**) |
| **`backend/scripts/`** | `seed_foods.py`, `seed_test_user.py` (Python path = `backend/`) |
| **`backend/docker-compose.yml`** | Optional Postgres / Redis / Elasticsearch for local dev |
| **`backend/.env.example`** | Template for `backend/.env` or repo-root `.env` |
| **`backend/.coveragerc`** | Coverage when run from `backend/` |
| **`backend/database/`** | SQL schema, migrations, seeds (reference / DBA) |
| **`backend/datasets/`** | Food CSVs used by `api/utils/seed.py` at startup |
| **`backend/instance/`** | Local SQLite (non-Windows) — gitignored |

## `frontend/` — React (Vite)

| Path | Purpose |
|------|---------|
| **`frontend/src/`** | App entry (`App.jsx`, `main.jsx`), **`lib/api.js`**, **`styles/index.css`**, **`pages/auth/`**, **`pages/app/`**, **`components/`**, **`context/`** |
| **`frontend/docs/`** | **`UI_DESIGN_GUIDE.md`** — layout and styling conventions |

## `models/` — offline ML (optional)

| Path | Purpose |
|------|---------|
| **`models/scripts/`** | `run_pipeline.py` — train sample recommender; reads **`backend/datasets/`** |
| **`models/notebooks/`** | Jupyter notebooks |
| **`models/output/`** | Plots and `.joblib` artifacts (local) |

## Root shims (convenience)

| Path | Purpose |
|------|---------|
| **`run.py`** | Delegates to `backend/run.py` (same as `python backend/run.py`) |
| **`requirements.txt`** | `-r backend/requirements.txt` so `pip install -r requirements.txt` still works |
| **`pyproject.toml`** | `pytest` defaults (`testpaths`, `pythonpath`) for the API |
| **`.env.example`** | Points to **`backend/.env.example`** |

## Documentation index

| Path | Purpose |
|------|---------|
| **`docs/ARCHITECTURE.md`** | System design |
| **`docs/PIPELINE.md`** | Dev, CI, Docker, offline ML |
| **`docs/STRUCTURE.md`** | This file |
| **`docs/guides/`** | HOW_TO_RUN, setup, troubleshooting |
| **`docs/reference/`**, **`docs/project/`** | Longer reference & audits |
| **`docs/architecture/`** | ER diagrams, implementation notes |
| **`docs/frontend/`** | Index → UI guide lives in **`frontend/docs/`** |

## Removed clutter (historical)

- **`apps/mobile/`** (Expo / React Native) — removed; this repository is **web-only** (`frontend/`).
- Legacy Node **`backend/`** that only held `node_modules` — delete manually if it reappears; **not** the current `backend/` package above.
- Stub **`ml-api/`**, root **`search/`**, **`api/rag/`** — removed earlier.

## Generated / local (do not commit)

`.gitignore`: `venv/`, `node_modules/`, `dist/`, `logs/`, `.env`, `__pycache__/`, `backend/instance/*.db`, coverage files.
