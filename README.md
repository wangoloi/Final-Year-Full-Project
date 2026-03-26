# Final year project — GlucoSense + Meal Plan (integrated)

You run **three processes**: Meal Plan API (**8001**), GlucoSense API + portal (**8000** + **5173**), Meal Plan UI (**5175**). GlucoSense keeps port **8000** for clinical APIs; the meal app must use **8001** so routes are not mixed up.

---

## How to start the full system

### Option A — One command (Windows, recommended)

1. Open **PowerShell**.
2. Go to the project root (the folder that contains `scripts` and `Glucosense`):

   ```powershell
   Set-Location -LiteralPath "e:\final year3;2 project"
   ```

   Use your real path; **`-LiteralPath`** is required if the folder name contains `;`.

3. Run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File ".\scripts\start-integrated.ps1"
   ```

4. **Three new windows** open (Meal API, GlucoSense, Meal Vite). Wait until each shows “Uvicorn running” or “VITE … ready”.

5. **Open the portal** in your browser: **http://localhost:5173**  
   If the GlucoSense window says port **5174** is in use, open **http://localhost:5174** instead.

6. **Confirm `.env`** in `Glucosense\Glucosense\frontend\` contains:

   ```env
   VITE_MEAL_PLAN_URL=http://localhost:5175
   VITE_MEAL_PLAN_API_URL=http://127.0.0.1:8001
   ```

   If you change these, **restart** `npm run start` for GlucoSense so Vite reloads env vars.

---

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
Set-Location -LiteralPath "e:\final year3;2 project\Glucosense\Glucosense\frontend"
npm run start
```

Wait for: `Uvicorn running` on **8000** and VITE on **5173** (or another port if 5173 is busy — read the terminal line `Local: http://localhost:…`).

**Terminal 3 — Meal Plan frontend (port 5175, proxies `/api` → 8001)**

```powershell
Set-Location -LiteralPath "e:\Glucosense app\Meal-Plan-System\frontend"
$env:MEAL_PLAN_API_PROXY = "http://127.0.0.1:8001"
node ./node_modules/vite/bin/vite.js --port 5175 --strictPort
```

---

### Quick health checks

| Check | What you should see |
|--------|---------------------|
| Meal API | Open **http://127.0.0.1:8001/api/health** → JSON with `"glocusense-meal-plan"` |
| GlucoSense API | Open **http://127.0.0.1:8000/api/health/live** → `{"status":"ok",…}` |
| Meal UI + proxy | Open **http://localhost:5175/api/health** → same meal-plan JSON as direct 8001 |

---

### URLs cheat sheet

| What | URL |
|------|-----|
| **Main app (open this)** | http://localhost:5173 (or 5174 if Vite printed that) |
| Meal Plan UI (standalone) | http://localhost:5175 |
| GlucoSense API docs | http://127.0.0.1:8000/docs |
| Meal Plan API docs | http://127.0.0.1:8001/docs |

---

## First-time setup (once per machine)

```powershell
Set-Location -LiteralPath ".\Glucosense\Glucosense"
python -m pip install -r requirements.txt

Set-Location -LiteralPath "..\..\Meal-Plan-System\backend"
python -m pip install -r requirements.txt

Set-Location -LiteralPath "..\..\..\Glucosense\Glucosense\frontend"
npm install

Set-Location -LiteralPath "..\..\Meal-Plan-System\frontend"
npm install
```

If your path contains `;`, always use `Set-Location -LiteralPath '…'`.

---

## What each piece does

| Piece | Folder | Role |
|-------|--------|------|
| **GlucoSense** | `Glucosense/Glucosense/` | Landing, login, clinician workspace, patient meal shell |
| **Meal Plan UI** | `Meal-Plan-System/frontend/` | Embedded at `/meal-plan`; dev server **5175** in integrated setup |
| **GlucoSense API** | Started from `Glucosense/.../frontend` via `npm run start` | **:8000** — clinical CDS |
| **Meal Plan API** | `Meal-Plan-System/backend` | **:8001** — auth, meals, SSO for embed |

---

## Configuration

| File | Purpose |
|------|---------|
| `Glucosense/Glucosense/frontend/.env` | `VITE_MEAL_PLAN_URL` (iframe) and `VITE_MEAL_PLAN_API_URL` (SSO → **8001**) |
| `Glucosense/Glucosense/frontend/.env.example` | Template |

---

## Docker deployment (production-like)

Run the **same integrated system** as containers on **8080** (GlucoSense), **8081** (Meal API), **8082** (Meal UI + nginx → API).

1. Copy `.env.deploy.example` to `.env.deploy` and set secrets for real deployments.
2. From the project root:

   ```powershell
   docker compose --env-file .env.deploy up --build
   ```

3. Open **http://localhost:8080**.

Full checklist, HTTPS, and secrets: **[DEPLOY.md](./DEPLOY.md)**.  
In **VS Code / Cursor**: **Terminal → Run Task → “Docker Compose: up (integrated)”** (requires `.env.deploy`).

---

## Documentation

| Doc | Purpose |
|-----|---------|
| **[ARCHITECTURE.md](./ARCHITECTURE.md)** | Components, ports, GlucoSense + Meal integration |
| **[SYSTEM_PIPELINE.md](./SYSTEM_PIPELINE.md)** | Full **application + ML pipeline** (runtime sequences, offline training, data paths) |
| **[DEPLOY.md](./DEPLOY.md)** | Docker Compose, HTTPS, secrets |

---

## Repo layout

```
Glucosense app/   (your workspace root)
├── README.md
├── ARCHITECTURE.md
├── SYSTEM_PIPELINE.md
├── DEPLOY.md
├── docker-compose.yml
├── .env.deploy.example
├── scripts/
│   └── start-integrated.ps1     ← starts all three stacks
├── Glucosense/Glucosense/
│   ├── frontend/                ← npm run start (API :8000 + Vite)
│   ├── backend/
│   ├── data/                    ← SmartSensor_DiabetesMonitoring.csv (default)
│   └── scripts/
│       └── run_smart_sensor_ml.py
└── Meal-Plan-System/
    ├── backend/                 ← PORT=8001 python run.py
    └── frontend/                ← Meal Vite (5175 integrated)
```

---

## Sign-in behavior (demo)

- **Clinician** → **/workspace** + Meal plan in sidebar.
- **Patient** → **/meal-plan** only.

---

## Troubleshooting

- **`Get-NetTCPConnection` hangs** in the script — use **Option B** (three terminals) instead.
- **Blank meal plan / 500 on `/api/auth/...`** — Meal API must be on **8001**; GlucoSense `.env` must have `VITE_MEAL_PLAN_API_URL=http://127.0.0.1:8001`; Meal Vite must use `MEAL_PLAN_API_PROXY=http://127.0.0.1:8001` (or rely on `vite.config.js` default **8001**).
- **Port already in use** — Close old dev servers or add **5175** to the ports the script clears; avoid running two Meal Vite servers.
- **Node out of memory** — Run `npm run dev:api` and `npm run dev` in separate terminals under GlucoSense `frontend` instead of `npm run start`; keep Meal API + Meal Vite running as above.
