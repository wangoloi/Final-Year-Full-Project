# Data

Place project datasets here.

| File | Description |
|------|-------------|
| `SmartSensor_DiabetesMonitoring.csv` | Default training CSV for **`clinical_insulin_pipeline`** — wearable-style rows. **Target:** `Insulin_Dose` (IU, clipped to 0–10 for training). **Not used as features:** `Predicted_Progression` (dropped to reduce leakage). Engineered features include cyclical time + `glycemic_stress_index`, `pulse_pressure`, `activity_volume`. |

**Note:** The **`insulin_system`** dashboard loader and legacy bundle format may expect a **different** column schema than this file. For **`outputs/best_model/inference_bundle.joblib`**, match whatever `load_best_model` expects.
