# GlucoSense — Integrated Clinical & Meal Planning Workspace

**GlucoSense** is a final-year integration project that combines a clinical insulin decision-support portal with a companion meal-planning system. The workspace demonstrates how clinical and nutrition apps can operate together while keeping clinical APIs and meal APIs separated.

> This project is educational/demo-only. Insulin and meal recommendations are assistive and should not be used instead of medical advice.

---

## Project summary

This repository contains two coordinated applications:

- **Clinical insulin support** (`Clinical-Insulin-Recommendation/`)
  - FastAPI backend
  - React frontend with Vite
  - Patient management, glucose assessment, insulin guidance, charts, alerts, and reports
  - Machine learning pipeline and model artifacts for insulin recommendation

- **Meal planning companion** (`Meal-Plan-System/`)
  - FastAPI backend
  - React frontend with Vite
  - Food search, meal recommendations, meal logging, and optional chatbot support
  - Separate database and API surface from the clinical app

These two apps are integrated so the GlucoSense portal can embed the meal planning experience while preserving clear boundary lines between the clinical and meal systems.

---

## Key features

- Clinician dashboard and patient assessment flow
- Model-assisted insulin guidance with visual context
- Separate meal planning UI and API, integrated by iframe and session flow
- Clear API separation: clinical API on `8000`, meal API on `8001`
- Windows-friendly integrated launch scripts
- Production-like Docker deployment support

---

## Repository layout

```text
Glucosense app/
├── .gitignore
├── ARCHITECTURE.md
├── DEPLOY.md
├── FRONTEND_BACKEND_AUDIT.md
├── README.md
├── SYSTEM_PIPELINE.md
├── docker-compose.yml
├── package.json
├── package-lock.json
├── scripts/
│   └── start-integrated.ps1
├── Clinical-Insulin-Recommendation/
│   ├── backend/
│   ├── frontend/
│   ├── data/
│   └── scripts/
└── Meal-Plan-System/
    ├── backend/
    ├── frontend/
    └── docs/
```

---

## Running the integrated workspace

### Recommended: integrated startup (Windows)

1. Open PowerShell at the repo root:

   ```powershell
   Set-Location -LiteralPath "e:\Glucosense app"
   ```

2. Start the integrated stack:

   ```powershell
   powershell -ExecutionPolicy Bypass -File ".\scripts\start-integrated.ps1"
   ```

3. Confirm three windows appear:
   - Meal Plan API on `8001`
   - GlucoSense API + portal on `8000` and `5173`
   - Meal Plan UI on `5175`

4. Open the portal at:

   ```text
   http://localhost:5173
   ```

---

## Manual startup (three terminals)

### Terminal 1 — Meal Plan API

```powershell
Set-Location -LiteralPath "e:\Glucosense app\Meal-Plan-System\backend"
$env:PORT = "8001"
python run.py
```

### Terminal 2 — GlucoSense API + portal

```powershell
Set-Location -LiteralPath "e:\Glucosense app\Clinical-Insulin-Recommendation\frontend"
npm run start
```

### Terminal 3 — Meal Plan frontend

```powershell
Set-Location -LiteralPath "e:\Glucosense app\Meal-Plan-System\frontend"
$env:MEAL_PLAN_API_PROXY = "http://127.0.0.1:8001"
node ./node_modules/vite/bin/vite.js --port 5175 --strictPort
```

---

## Port map

| Component | Port |
|-----------|------|
| Clinical API | `8000` |
| Clinical frontend | `5173` |
| Meal API | `8001` |
| Meal frontend | `5175` |

---

## First-time setup

```powershell
Set-Location -LiteralPath ".\Clinical-Insulin-Recommendation"
python -m pip install -r requirements.txt

Set-Location -LiteralPath "..\Meal-Plan-System\backend"
python -m pip install -r requirements.txt

Set-Location -LiteralPath "..\Clinical-Insulin-Recommendation\frontend"
npm install

Set-Location -LiteralPath "..\Meal-Plan-System\frontend"
npm install
```

---

## Useful commands

| Command | Location | Purpose |
|---|---|---|
| `npm run dev:fast` | `Clinical-Insulin-Recommendation/frontend` | Start the clinical API + frontend |
| `npm run start` | repo root | Start integrated environment |
| `npm run dev` | `Meal-Plan-System/frontend` | Start meal UI |
| `python run.py` | `Meal-Plan-System/backend` | Start meal API |

---

## Configuration

| File | Purpose |
|------|---------|
| `Clinical-Insulin-Recommendation/frontend/.env` | `VITE_MEAL_PLAN_URL` and `VITE_MEAL_PLAN_API_URL` |
| `Clinical-Insulin-Recommendation/frontend/.env.example` | Template for frontend env settings |

---

## Docker deployment

- Use `docker-compose.yml` and copy `.env.deploy.example` to `.env.deploy`
- Run:

```powershell
docker compose --env-file .env.deploy up --build
```

- Open:

```text
http://localhost:8080
```

For full details, see `DEPLOY.md`.

---

## Architecture & docs

| File | Description |
|------|-------------|
| `ARCHITECTURE.md` | System architecture and integration design |
| `SYSTEM_PIPELINE.md` | Data pipeline, ML artifacts, training flow |
| `DEPLOY.md` | Deployment and Docker setup |
| `FRONTEND_BACKEND_AUDIT.md` | Frontend/backend audit notes |
| `Clinical-Insulin-Recommendation/docs/README.md` | Clinical app documentation index |
| `Meal-Plan-System/docs/README.md` | Meal plan documentation index |

---

## Troubleshooting

- If the integrated script hangs on TCP checks, start the components manually.
- If the meal app fails to authenticate, verify `VITE_MEAL_PLAN_API_URL` points to `http://127.0.0.1:8001`.
- If ports are busy, stop existing dev servers before restarting.
- If Vite runs out of memory, start the backend and frontend separately.

---

## Authors

- Abaho Joy
- Wangolo Bachawa
- Mucunguzi Godfrey


