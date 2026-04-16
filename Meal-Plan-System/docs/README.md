# Meal-Plan-System — documentation index

**Product:** FastAPI (`backend/`) + React/Vite (`frontend/`). No mobile app in this repo.

**Monorepo (GlucoSense + Meal Plan):** [../../SYSTEM_PIPELINE.md](../../SYSTEM_PIPELINE.md) · [../../ARCHITECTURE.md](../../ARCHITECTURE.md) (workspace root).

| Document | Description |
|----------|-------------|
| **[DESIGN_STRUCTURE.md](./DESIGN_STRUCTURE.md)** | **Primary reference:** technology stack, layout, routers, engine, directories, ports, env vars. |
| [PIPELINE.md](./PIPELINE.md) | Local dev, CI, GitHub Actions, Docker builds, optional ML pipeline. |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Production-oriented notes. |

**Tech stack table:** at the top of [DESIGN_STRUCTURE.md](./DESIGN_STRUCTURE.md) and in the project [README.md](../README.md).

### Guides (`guides/`)

| File | Description |
|------|-------------|
| [HOW_TO_RUN.md](./guides/HOW_TO_RUN.md) | Run API + frontend, Windows `;` paths, ports (**8001** / **5175**), troubleshooting. |
| [CHATBOT.md](./guides/CHATBOT.md) | RAG + LLM chatbot (`/api/chatbot`). |
| [TYPESENSE.md](./guides/TYPESENSE.md) | Optional Typesense-backed search. |
| [TROUBLESHOOTING.md](./guides/TROUBLESHOOTING.md) | Common issues. |
| [LEGACY_FOLDER_CLEANUP.md](./guides/LEGACY_FOLDER_CLEANUP.md) | Removing stray old Node `backend/` folders. |

### Architecture notes (`architecture/`)

| File | Description |
|------|-------------|
| [ER_DIAGRAM.md](./architecture/ER_DIAGRAM.md) | ER / schema notes. |
| [VECTOR_DB_SCHEMA.md](./architecture/VECTOR_DB_SCHEMA.md) | Vector store notes. |

### Frontend

| Path | Description |
|------|-------------|
| [frontend/README.md](./frontend/README.md) | Index → [`../frontend/docs/UI_DESIGN_GUIDE.md`](../frontend/docs/UI_DESIGN_GUIDE.md) |
