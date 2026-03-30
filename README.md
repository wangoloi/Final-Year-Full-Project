# GlucoSense — integrated diabetes support (clinical + meal planning)

**GlucoSense** is a final-year project that combines two applications in one workspace: a **clinical insulin decision-support portal** and a **meal-planning companion**. Together they help demonstrate how people with diabetes (especially Type 1–oriented workflows) might use software for **education and decision support** — not as a replacement for a doctor or diabetes team.

Everything here is **demo / educational**. Insulin suggestions and meal advice are **assistive only**; a qualified clinician must validate any real-world dosing or care decisions.

---

## What this system is (in plain language)

| Part | What it does |
|------|----------------|
| **GlucoSense (clinical)** | Lets clinicians register patients, record assessments and glucose, get **model-assisted insulin guidance** with explanations where available, log doses, see trends, alerts, and reports. Patients get a focused entry to nutrition features. |
| **Meal Plan (Glocusense)** | A separate app for **food search**, **meal recommendations**, **glucose logging** in that product, and an optional **chatbot** (RAG + LLM when configured). It has its own database and API. |
| **Integration** | The main GlucoSense portal **embeds** the meal app in an iframe and uses **single sign-on (SSO)** so users do not log in twice. Clinicians see the meal tools inside the workspace; patients can use a full-screen meal experience. |

So: **one browser experience** (GlucoSense UI), **two backends** (clinical on one port, meals on another), wired so routes and data stay separate and clear.

---

## How the system works (big picture)

1. **You start three processes in development:** GlucoSense API + web UI, Meal Plan API, and Meal Plan web UI. Each piece listens on its own port so **clinical APIs (8000)** never clash with **meal APIs (8001)**.
2. **Clinician flow:** Sign in → open the **workspace** → manage patients → run an **assessment** on the dashboard → the GlucoSense backend loads the **inference model bundle** (when present), runs recommendation logic, saves to **SQLite**, and may raise **alerts**. Charts and reports use stored readings and events.
3. **Meal flow:** The GlucoSense frontend loads the meal app from a URL (e.g. `localhost:5175`). It asks the meal API for a **JWT** and passes it into the iframe so the meal app knows who is signed in. Food search, chat, and recommendations talk to the **meal API** only.
4. **Offline / ML:** Training scripts and CSV data live under `Clinical-Insulin-Recommendation/`; outputs go to predictable folders (see **[SYSTEM_PIPELINE.md](./SYSTEM_PIPELINE.md)**). Runtime inference uses bundled artifacts when available.

For ports, components, and sequence diagrams, see **[ARCHITECTURE.md](./ARCHITECTURE.md)**.

---

## Repository layout

| Folder | Role |
|--------|------|
| **`Clinical-Insulin-Recommendation/`** | GlucoSense: FastAPI backend, React (Vite) portal, SQLite, clinical ML pipeline and data |
| **`Meal-Plan-System/`** | Meal Plan: FastAPI backend, React (Vite) UI, SQLite, optional RAG/LLM and search |
| **`scripts/`** | Integrated launchers — see [`scripts/README.md`](scripts/README.md) |

```
Glucosense app/
├── README.md                 ← this file
├── ARCHITECTURE.md           ← detailed components and integration
├── SYSTEM_PIPELINE.md        ← app + ML pipeline, data paths
├── DEPLOY.md                 ← Docker, HTTPS, secrets
├── docker-compose.yml
├── .env.deploy.example
├── scripts/
│   └── start-integrated.ps1
├── Clinical-Insulin-Recommendation/
│   ├── frontend/             ← npm run start (API :8000 + Vite)
│   ├── backend/
│   ├── data/                 ← e.g. SmartSensor_DiabetesMonitoring.csv
│   └── scripts/
└── Meal-Plan-System/
    ├── backend/              ← PORT=8001 python run.py
    └── frontend/             ← Meal Vite (5175 in integrated dev)
```

---

## Quick start (integrated dev)

You run **three processes**: Meal Plan API (**8001**), GlucoSense API + portal (**8000** + **5173**), Meal Plan UI (**5175**). GlucoSense keeps **8000** for clinical APIs; the meal app uses **8001** so routes are not mixed.

### Option A — One command (Windows, recommended)

1. Open **PowerShell** and go to this repo root (the folder that contains `scripts` and `Clinical-Insulin-Recommendation`). If the path contains `;`, use **`-LiteralPath`**:

   ```powershell
   Set-Location -LiteralPath "e:\Glucosense app"
   ```

2. Run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File ".\scripts\start-integrated.ps1"
   ```

3. **Three new windows** open. Wait until each shows “Uvicorn running” or “VITE … ready”.
4. Open the **main app**: **http://localhost:5173** (or **5174** if Vite chose another port).
5. Ensure `Clinical-Insulin-Recommendation\frontend\.env` contains:

   ```env
   VITE_MEAL_PLAN_URL=http://localhost:5175
   VITE_MEAL_PLAN_API_URL=http://127.0.0.1:8001
   ```

   Restart `npm run start` for GlucoSense after changing env vars.

### Option B — Three terminals (manual)

Use **three** terminals. Order: start **Meal API** first, then **GlucoSense**, then **Meal Vite**.

**Terminal 1 — Meal Plan API (port 8001)**

```powershell
Set-Location -LiteralPath "e:\Glucosense app\Meal-Plan-System\backend"
$env:PORT = "8001"
python run.py
```

Wait for: `Uvicorn running on http://0.0.0.0:8001`

**Terminal 2 — GlucoSense API + portal**

```powershell
Set-Location -LiteralPath "e:\Glucosense app\Clinical-Insulin-Recommendation\frontend"
npm run start
```

Wait for: `Uvicorn running` on **8000** and Vite on **5173** (or another port if 5173 is busy — read the terminal line `Local: http://localhost:…`).

**Terminal 3 — Meal Plan frontend (port 5175, proxies `/api` → 8001)**

```powershell
Set-Location -LiteralPath "e:\Glucosense app\Meal-Plan-System\frontend"
$env:MEAL_PLAN_API_PROXY = "http://127.0.0.1:8001"
node ./node_modules/vite/bin/vite.js --port 5175 --strictPort
```

### Health checks

| Check | URL | Expected |
|-------|-----|----------|
| Meal API | http://127.0.0.1:8001/api/health | JSON with `"glocusense-meal-plan"` |
| GlucoSense API | http://127.0.0.1:8000/api/health/live | `{"status":"ok",…}` |
| Meal UI + proxy | http://localhost:5175/api/health | Same meal-plan JSON as direct 8001 |

### URLs cheat sheet

| What | URL |
|------|-----|
| **Main app** | http://localhost:5173 (or 5174) |
| Meal Plan UI (standalone) | http://localhost:5175 |
| GlucoSense API docs | http://127.0.0.1:8000/docs |
| Meal Plan API docs | http://127.0.0.1:8001/docs |

---

## First-time setup (once per machine)

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

## Configuration

| File | Purpose |
|------|---------|
| `Clinical-Insulin-Recommendation/frontend/.env` | `VITE_MEAL_PLAN_URL` (iframe) and `VITE_MEAL_PLAN_API_URL` (SSO → **8001**) |
| `Clinical-Insulin-Recommendation/frontend/.env.example` | Template |

---

## Docker (production-like)

Same integrated system as containers: **8080** (GlucoSense), **8081** (Meal API), **8082** (Meal UI + nginx → API).

1. Copy `.env.deploy.example` to `.env.deploy` and set secrets.
2. From the project root: `docker compose --env-file .env.deploy up --build`
3. Open **http://localhost:8080**

Details: **[DEPLOY.md](./DEPLOY.md)**

---

## Sign-in behavior (demo)

- **Clinician** → **/workspace** (dashboard, patients, embedded meal plan in sidebar).
- **Patient** → **/meal-plan** (full-screen meal shell).

---

## Documentation index

| Doc | Content |
|-----|---------|
| **[ARCHITECTURE.md](./ARCHITECTURE.md)** | Components, ports, integration, end-to-end flows |
| **[SYSTEM_PIPELINE.md](./SYSTEM_PIPELINE.md)** | Application + ML pipeline, training, data artifacts |
| **[DEPLOY.md](./DEPLOY.md)** | Docker Compose, HTTPS, secrets |
| `Clinical-Insulin-Recommendation/docs/README.md` | GlucoSense-specific docs index |
| `Meal-Plan-System/docs/README.md` | Meal Plan docs index |

---

## Troubleshooting (short)

- **`Get-NetTCPConnection` hangs** in the integrated script — use three terminals manually.
- **Blank meal plan / errors on meal auth** — Meal API on **8001**; GlucoSense `.env` must point `VITE_MEAL_PLAN_API_URL` to **8001**; Meal Vite must proxy to **8001**.
- **Port already in use** — Stop old dev servers; avoid two Meal Vite instances on **5175**.
- **Node out of memory** — Split GlucoSense into `npm run dev:api` and `npm run dev` in separate terminals; keep Meal API + Meal Vite as usual.

---

## Authors

**Abaho Joy**
**Wangolo Bachawa**
**Mucunguzi Godfrey**


