# GlucoSense documentation

| Document | Description |
|----------|--------------|
| **[STRUCTURE.md](STRUCTURE.md)** | Repository layout: `backend/`, `frontend/`, `data/`, `scripts/`, `outputs/`. |
| **[RUN.md](RUN.md)** | Run the clinical insulin training pipeline, API, frontend, troubleshooting. |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | System structure, C4-style views, layers, repo map. |
| **[PIPELINE.md](PIPELINE.md)** | Runtime seed/DB flow and how training artifacts relate to the API. |
| **[INPUT_FLOW.md](INPUT_FLOW.md)** | Patient and assessment input handling. |
| **[CDS_SAFETY_ENGINE.md](CDS_SAFETY_ENGINE.md)** | Clinical decision support safety behaviour. |
| **[UGANDA_T1D_GUIDELINES.md](UGANDA_T1D_GUIDELINES.md)** | Uganda T1D guideline JSON and dosing context. |

**Training package:** `backend/src/clinical_insulin_pipeline/` — run via **`python run_clinical_insulin_pipeline.py`** (see [scripts/README.md](../scripts/README.md)).

**Workspace-wide** (GlucoSense + Meal Plan + integrated ports): **[../../../SYSTEM_PIPELINE.md](../../../SYSTEM_PIPELINE.md)** · **[../../../README.md](../../../README.md)**.
