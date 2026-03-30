# GlucoSense (Clinical-Insulin-Recommendation) scripts

| Path | Purpose |
|------|---------|
| **`launcher.py`** | Start backend + frontend (see repo root `launcher.py` shim). |
| **`pipeline/run_clinical_insulin_pipeline.py`** | Train insulin dose regression (0–10 IU), write `outputs/clinical_insulin_pipeline/latest/`. |
| **`dev/quick_clinical_check.py`** | Quick RF smoke test on `data/SmartSensor_DiabetesMonitoring.csv`. |
| **`windows/`** | Windows helpers: `run_dev.ps1`, `run_dev_network.ps1`, `setup_venv.ps1`, `ngrok_tunnel.ps1`, `run_all.ps1`. |

From **Clinical-Insulin-Recommendation** repo root you can still run:

`python run_clinical_insulin_pipeline.py` (delegates to `scripts/pipeline/`).
