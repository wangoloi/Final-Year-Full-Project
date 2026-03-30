# Documentation index

**Product shape:** **FastAPI** (`backend/`) + **React/Vite** (`frontend/`). There is **no** mobile app in this repo.

**Integrated workspace (GlucoSense + this app):** see **[../../../SYSTEM_PIPELINE.md](../../../SYSTEM_PIPELINE.md)** and **[../../../ARCHITECTURE.md](../../../ARCHITECTURE.md)** at the monorepo root.

| Document | Description |
|----------|-------------|
| [STRUCTURE.md](./STRUCTURE.md) | Repository folder layout |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Current FastAPI + Vite architecture |
| [PIPELINE.md](./PIPELINE.md) | Development, quality checks, CI, Docker, ML offline |
| [guides/HOW_TO_RUN.md](./guides/HOW_TO_RUN.md) | Run commands, Windows `;` path, timeouts |
| [guides/CHATBOT.md](./guides/CHATBOT.md) | RAG + LLM chatbot (`/api/chatbot/message`) |
| [guides/TYPESENSE.md](./guides/TYPESENSE.md) | Optional Typesense-backed food search |
| [guides/SETUP_GUIDE.md](./guides/SETUP_GUIDE.md) | Environment setup |
| [guides/LEGACY_FOLDER_CLEANUP.md](./guides/LEGACY_FOLDER_CLEANUP.md) | Removing old Node `backend/` junk only |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Production-oriented notes |
| [reference/SYSTEM_DOCUMENTATION.md](./reference/SYSTEM_DOCUMENTATION.md) | Long reference (some sections mix history with current API) |
| [../frontend/vite.config.js](../frontend/vite.config.js) | Dev server **5175**, proxy `/api` → **8001** by default |
| [project/](./project/) | Audits & coursework-style summaries |

Frontend UI notes: [`frontend/docs/UI_DESIGN_GUIDE.md`](../frontend/docs/UI_DESIGN_GUIDE.md) · [docs/frontend index](./frontend/README.md)
