"""Repository root and default paths for pipeline scripts (run from any cwd)."""
from pathlib import Path

# This file lives in scripts/pipeline/
REPO_ROOT: Path = Path(__file__).resolve().parents[2]
SRC: Path = REPO_ROOT / "backend" / "src"
DEFAULT_DATA_CSV: Path = REPO_ROOT / "data" / "SmartSensor_DiabetesMonitoring.csv"
