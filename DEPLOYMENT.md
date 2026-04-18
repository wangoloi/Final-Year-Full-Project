# Production deployment (Netlify + cloud APIs)

This document describes how to run **GlucoSense (Clinical)** and **Meal Plan** on the public internet with **Netlify** frontends and **hosted** FastAPI backends (Render, Railway, Fly.io, AWS, GCP, etc.).

## Shared secrets (must match)

| Secret | Where |
|--------|--------|
| `JWT_SECRET` | Meal Plan API — signs user JWTs |
| `MEAL_PLAN_JWT_SECRET` | Clinical API — **same value** as Meal Plan `JWT_SECRET` for Bearer validation |
| `GLUCOSENSE_EMBED_KEY` | Meal Plan API + GlucoSense `VITE_MEAL_PLAN_EMBED_SECRET` (iframe SSO) |
| `GLUCOSENSE_API_KEY` | Optional service key for Clinical API (`X-API-Key`) |
| `GLUCOSENSE_REQUIRE_AUTH` | Set `true` on Clinical API in production |

## Meal Plan API (FastAPI)

1. Set `DATABASE_URL` to PostgreSQL, e.g. `postgresql+psycopg2://user:pass@host:5432/glocusense`
2. Set `JWT_SECRET` to a long random string (32+ bytes).
3. Set `CORS_EXTRA_ORIGINS` to your Netlify Meal Plan site URL(s), comma-separated.
4. Run with Gunicorn + Uvicorn workers (from `Meal-Plan-System/backend`):

```bash
gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:${PORT:-8001} api.main:app
```

5. Health check: `GET /health`

## Clinical API (GlucoSense)

1. From repository root `Clinical-Insulin-Recommendation`:

```bash
gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:${PORT:-8000} app:app
```

2. Environment:
   - `MEAL_PLAN_JWT_SECRET` = same as Meal Plan `JWT_SECRET`
   - `GLUCOSENSE_REQUIRE_AUTH=true`
   - `CORS_ALLOW_ORIGINS=https://your-glucosense.netlify.app` (comma-separated if multiple)
   - Optional: `GLUCOSENSE_API_KEY` for automation / server-to-server

3. Health check: `GET /api/health/live`

## Netlify — Meal Plan SPA (`Meal-Plan-System/frontend`)

- **Build command:** `npm run build`
- **Publish directory:** `dist`
- **SPA redirects:** `netlify.toml` is included (all routes → `index.html`).
- **Environment variables (Vite):**
  - `VITE_MEAL_PLAN_API_URL` — public Meal Plan API URL (if needed by client)
  - Any existing `VITE_*` keys your app uses

## Netlify — GlucoSense SPA (`Clinical-Insulin-Recommendation/frontend`)

- **Build command:** `npm run build`
- **Publish directory:** `dist`
- **Environment variables:**
  - `VITE_MEAL_PLAN_URL` — Netlify URL of Meal Plan SPA (iframe)
  - `VITE_MEAL_PLAN_API_URL` — public Meal Plan **API** base URL (must be reachable from browser for login)
  - `VITE_CLINICAL_API_URL` — public Clinical API base URL (e.g. `https://glucosense-api.onrender.com` with **no** trailing slash). Leave empty in local dev (Vite proxy uses `/api`).

## Role accounts (clinician)

Public registration creates **patient** users only. To grant **clinician**:

- Update the user row in the Meal Plan database: `UPDATE users SET role = 'clinician' WHERE email = '...';`
- Or use `Meal-Plan-System/backend/scripts/promote_clinician.py` (see script help).

## CORS and cookies

Clinical API uses Bearer tokens in `Authorization`, not cookies, so **CSRF** to the API is not the primary concern. Restrict `CORS_ALLOW_ORIGINS` to your Netlify domains in production.

## Load testing

k6 scripts live under `scripts/loadtest/`. Run them only against staging or with permission.
