# GlucoSense monorepo scripts (repo root)

Scripts that coordinate **Clinical-Insulin-Recommendation**, **Meal-Plan-System**, and ports.

| File | Purpose |
|------|---------|
| **`start-integrated.ps1`** | Full stack: Meal API :8001, GlucoSense :8000/:5173, Meal Vite :5175 (three windows). |
| **`free-dev-ports.ps1`** | Free common dev ports (8000, 8001, 5173–5175). |
| **`run-full-stack.ps1`** / **`.cmd`** | Alternative full-stack launcher. |
| **`run-full-stack-clean.cmd`** | Clean restart variant. |
| **`run-meal-dev.ps1`** / **`.cmd`** | Meal Plan dev only. |

Application-specific scripts live under each project, e.g. `Clinical-Insulin-Recommendation/scripts/`.
