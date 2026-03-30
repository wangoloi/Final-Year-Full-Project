# Meal-Plan-System — pipelines

This document describes **how code moves** from development to checks and deployment for the Meal Plan stack (FastAPI + Vite).

## 1. Local development

| Step | Command | Notes |
|------|---------|--------|
| Python deps | `pip install -r requirements.txt` | Root `requirements.txt` includes `backend/requirements.txt` |
| API | `python backend/run.py` | Default **:8001** (`PORT` overrides) |
| Web | `cd frontend && npm install && npm run dev` | **:5175** (see `frontend/vite.config.js`); `/api` → proxy to API |
| One-shot (Windows) | `.\scripts\start_full_system.ps1` | Installs deps and opens API + Vite in new windows |

If the API runs on another port, set `MEAL_PLAN_API_PROXY` before `npm run dev` (see [guides/HOW_TO_RUN.md](./guides/HOW_TO_RUN.md)).

## 2. Quality gate (local CI parity)

Run the same checks as GitHub Actions before pushing:

**Windows (PowerShell), from `Meal-Plan-System/`:**

```powershell
.\scripts\ci.ps1
```

**Manual equivalent:**

```bash
# From Meal-Plan-System/
python -m pytest backend/tests -q
cd frontend && npm ci && npm run build
```

## 3. Continuous integration (GitHub Actions)

Workflow: **`.github/workflows/meal-plan-ci.yml`** (monorepo root).

- Triggers on changes under `Meal-Plan-System/**`.
- **Backend:** `pip install -r backend/requirements.txt` → `pytest backend/tests`.
- **Frontend:** `npm ci` → `npm run build`.

## 4. Offline ML pipeline (optional)

Not used by the live API at request time; for experiments and artifacts.

| Step | Command |
|------|---------|
| Train / EDA | `python models/scripts/run_pipeline.py` (from repo `Meal-Plan-System/`) |
| Windows helper | `scripts\windows\run_meal_pipeline.bat` |

Outputs go to `models/output/`. See `models/README.md`.

## 5. Container images

From **`Meal-Plan-System/`** (build context = this directory):

```bash
docker build -f docker/Dockerfile.api .
docker build -f docker/Dockerfile.web .
```

Integrated stack with GlucoSense uses the workspace `docker-compose.yml` (see repo root `DEPLOY.md`).

## 6. Optional infrastructure

| File | Purpose |
|------|---------|
| `backend/docker-compose.yml` | Local Postgres / Redis / Elasticsearch |
| `backend/docker-compose.typesense.yml` | Typesense for search ([guides/TYPESENSE.md](./guides/TYPESENSE.md)) |

---

See also: [STRUCTURE.md](./STRUCTURE.md), [ARCHITECTURE.md](./ARCHITECTURE.md), [guides/HOW_TO_RUN.md](./guides/HOW_TO_RUN.md).
