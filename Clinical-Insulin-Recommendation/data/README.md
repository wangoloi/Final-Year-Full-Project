# Data

Place project datasets here.

| File | Description |
|------|-------------|
| `SmartSensor_DiabetesMonitoring.csv` | Default dataset for the **Smart Sensor ML** pipeline (`scripts/run_smart_sensor_ml.py`) — 15-minute wearable-style rows, `Insulin_Dose` target. |

**Note:** The legacy `insulin_system` `DataProcessingPipeline` (dashboard reference load, older notebooks) expects a different column schema (`patient_id`, `Insulin`, `gender`, etc.). Use `scripts/run_smart_sensor_ml.py` for this CSV, or supply a legacy-formatted CSV via `--data` if you still run the old evaluation scripts.
