# ml-services

Standalone Python modules (embedding pipeline, hybrid recommender, RAG-style chatbot helpers, glucose analytics). **Not imported by the main FastAPI app** (`api/`); use for experiments, batch jobs, or future microservices.

See **[`docs/DESIGN_STRUCTURE.md`](../docs/DESIGN_STRUCTURE.md)** for how the shipping FastAPI app is structured; these modules are optional experiments not wired into `api/` by default.
