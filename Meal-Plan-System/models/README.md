# models (training / pipelines)

Offline ML and notebooks. Run from the **repository root** (the folder that contains `backend/` and `models/`):

```bash
python models/scripts/run_pipeline.py
```

Or use `scripts/windows/run_meal_pipeline.bat`.

| Path | Purpose |
|------|---------|
| **`scripts/run_pipeline.py`** | Trains the sample meal recommendation model; writes artifacts to **`output/`** |
| **`notebooks/`** | Jupyter experiments (e.g. meal recommendation exploration) |
| **`output/`** | Generated plots and `.joblib` — ignored by git (folder kept via `.gitkeep`) |
