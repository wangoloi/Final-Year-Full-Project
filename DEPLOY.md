# Deploying the integrated system (GlucoSense + Meal Plan)

This workspace can run as **three Docker services**: clinical portal + APIs on the host ports below.

## ML and training artifacts

Docker **does not** run the full training pipeline on container start. The GlucoSense image expects an **inference bundle** under `outputs/best_model/` (built offline with `Clinical-Insulin-Recommendation` scripts) unless you mount a volume with a pre-trained bundle. The **Smart Sensor** coursework-style pipeline (`scripts/run_smart_sensor_ml.py`) writes to `outputs/smart_sensor_ml/` and is documented in **[SYSTEM_PIPELINE.md](./SYSTEM_PIPELINE.md)**.

---

## What you get

| Service | Container | Host URL | Purpose |
|--------|-----------|----------|---------|
| GlucoSense | `glucosense` | **http://localhost:8080** | Landing, login, workspace, meal iframe (`PUBLIC_GLUCOSENSE_URL`) |
| Meal Plan API | `meal-api` | **http://localhost:8081** | Auth, SSO, nutrition API |
| Meal Plan UI | `meal-web` | **http://localhost:8082** | SPA served by nginx; `/api` proxied to meal-api |

The GlucoSense image is built with `VITE_MEAL_PLAN_URL` and `VITE_MEAL_PLAN_API_URL` pointing at those host URLs so the browser can load the iframe and run SSO.

## Prerequisites

- **Docker** + **Docker Compose** v2
- At least **8 GB RAM** free (Meal Plan stack includes ML / vector dependencies; first start can be slow)
- **Disk**: several GB for images and Hugging Face / embedding caches on first meal-api run

## Quick start (local / demo)

From the **repository root** (`final year3;2 project`):

```powershell
Copy-Item .env.deploy.example .env.deploy
docker compose --env-file .env.deploy up --build
```

Open **http://localhost:8080**. Sign in as clinician or patient; meal embed uses **8082** and SSO calls **8081**.

Stop:

```powershell
docker compose --env-file .env.deploy down
```

## Production hardening (checklist)

1. **Secrets** — In `.env.deploy`, set strong random values for `JWT_SECRET` and `GLUCOSENSE_EMBED_KEY`. Rebuild GlucoSense after changing `GLUCOSENSE_EMBED_KEY` so the SPA embed secret matches the API.
2. **HTTPS** — Put **Caddy**, **nginx**, or a cloud load balancer in front; terminate TLS there. Before `docker compose build`, set **`PUBLIC_GLUCOSENSE_URL`**, **`PUBLIC_MEAL_WEB_URL`**, and **`PUBLIC_MEAL_API_URL`** to your public `https://` origins so the GlucoSense SPA, meal SPA (postMessage allowlist), and SSO calls stay consistent.
3. **CORS** — Add your real origins to `CORS_EXTRA_ORIGINS` (comma-separated) for the Meal Plan API.
4. **Database** — SQLite in volumes is fine for demos. For production, point `DATABASE_URL` on `meal-api` to PostgreSQL (requires code/config changes) and use a managed DB for GlucoSense outputs if needed.
5. **Clinical use** — This stack is a **decision-support / education** demo. Follow your institution’s governance, consent, and validation rules before any real patient use.

## Building without Compose

- **GlucoSense image** (from `Clinical-Insulin-Recommendation`):

  ```bash
  docker build -t glucosense \
    --build-arg VITE_MEAL_PLAN_URL=https://meal.example.com \
    --build-arg VITE_MEAL_PLAN_API_URL=https://api-meal.example.com \
    --build-arg VITE_MEAL_PLAN_EMBED_SECRET=your-secret \
    .
  ```

- **Meal API / Meal Web** — use `Meal-Plan-System/docker/Dockerfile.api` and `Meal-Plan-System/docker/Dockerfile.web` (build context `Meal-Plan-System/`) as in `docker-compose.yml`.

## VS Code / Cursor

Run task **“Docker Compose: up (integrated)”** from **Terminal → Run Task** to start the same stack (see `.vscode/tasks.json`).

## Troubleshooting

- **`meal-api` unhealthy** — First boot can take minutes while Python loads ML deps. Increase `start_period` in `docker-compose.yml` if needed.
- **Blank meal iframe** — Confirm **8082** is reachable and `.env.deploy` URLs match what you put in the GlucoSense build args.
- **SSO 403** — `GLUCOSENSE_EMBED_KEY` in meal-api must match `VITE_MEAL_PLAN_EMBED_SECRET` used when building the GlucoSense frontend (Compose wires both from the same env var).
