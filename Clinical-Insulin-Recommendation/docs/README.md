# GlucoSense (Clinical-Insulin-Recommendation) — documentation

| Document | Description |
|----------|-------------|
| **[DESIGN_STRUCTURE.md](DESIGN_STRUCTURE.md)** | **Primary reference:** C4 context, layers, repo tree, `insulin_system` / `clinical_insulin_pipeline`, assessment→dose flow, frontend map, cross-cutting concerns. |
| **[RUN.md](RUN.md)** | Install dependencies, train pipeline, run API + frontend, troubleshooting. |
| **[PIPELINE.md](PIPELINE.md)** | Seed data, DB tables, training outputs vs runtime bundle. |
| **[CDS_SAFETY_ENGINE.md](CDS_SAFETY_ENGINE.md)** | CDS safety behaviour (glucose bands, hard stops, risk flags). |
| **[UGANDA_T1D_GUIDELINES.md](UGANDA_T1D_GUIDELINES.md)** | Uganda T1D guideline summary and `config/*.json` pointers. |
| **[notebooks/README.md](notebooks/README.md)** | Optional Jupyter; reproducible training uses `run_clinical_insulin_pipeline.py`. |

**Training package:** `backend/src/clinical_insulin_pipeline/` — see [scripts/README.md](../scripts/README.md).

**Whole workspace** (GlucoSense + Meal Plan): [../../../SYSTEM_PIPELINE.md](../../../SYSTEM_PIPELINE.md) · [../../../README.md](../../../README.md) · [../../../ARCHITECTURE.md](../../../ARCHITECTURE.md).

**Tech stack overview:** see the table at the top of **[DESIGN_STRUCTURE.md](DESIGN_STRUCTURE.md)** and the project **[README.md](../README.md)**.
