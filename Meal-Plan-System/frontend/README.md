# Glocusense frontend

React SPA built with **Vite**. Dev server default: **http://localhost:5175** (`vite.config.js`).

API calls use **`/api/...`**; Vite proxies to the Meal Plan API (**http://127.0.0.1:8001** by default — same as `python run.py` from `backend/`). Override with **`MEAL_PLAN_API_PROXY`** if the API uses another port.

New users see a one-time **onboarding** screen; completion calls **`POST /api/auth/onboarding/complete`**. Profile updates use **`PATCH /api/auth/profile`**.

## Commands

```bash
npm install
npm run dev      # development
npm run build    # production bundle → dist/
```

## Project docs

- Run & troubleshoot: [../docs/guides/HOW_TO_RUN.md](../docs/guides/HOW_TO_RUN.md)
- UI notes: [docs/UI_DESIGN_GUIDE.md](./docs/UI_DESIGN_GUIDE.md)
