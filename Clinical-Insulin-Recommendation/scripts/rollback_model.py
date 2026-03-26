"""
Rollback to a previous model version.

Usage:
  python scripts/rollback_model.py           # list versions
  python scripts/rollback_model.py --to 2    # rollback to v2
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from insulin_system.persistence import list_model_versions, load_best_model

DEFAULT_MODEL_DIR = Path("outputs/best_model")
BUNDLE_FILENAME = "inference_bundle.joblib"
METADATA_FILENAME = "metadata.json"


def main(model_dir: Path = DEFAULT_MODEL_DIR, to_version: int | None = None) -> int:
    versions = list_model_versions(model_dir)
    if not versions:
        print("No versioned models found. Run deploy_best_from_experiments.py first.")
        return 1

    if to_version is None:
        print("Available versions:", versions)
        print("Usage: python scripts/rollback_model.py --to <version>")
        return 0

    if to_version not in versions:
        print(f"Version {to_version} not found. Available: {versions}")
        return 1

    version_dir = model_dir / "versions" / f"v{to_version}"
    bundle_path = model_dir / BUNDLE_FILENAME
    meta_path = model_dir / METADATA_FILENAME

    # Backup current (optional)
    if bundle_path.exists():
        backup = model_dir / f"{BUNDLE_FILENAME}.bak"
        shutil.copy2(bundle_path, backup)
        shutil.copy2(meta_path, model_dir / f"{METADATA_FILENAME}.bak")
        print(f"Backed up current to .bak")

    # Copy version to current
    shutil.copy2(version_dir / BUNDLE_FILENAME, bundle_path)
    shutil.copy2(version_dir / METADATA_FILENAME, meta_path)
    print(f"Rolled back to v{to_version}")

    # Verify load
    try:
        b = load_best_model(model_dir)
        print(f"Verified: loaded model {getattr(b, 'model_name', '?')}")
    except Exception as e:
        print(f"Warning: load verification failed: {e}")
        return 1
    return 0


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    p.add_argument("--to", type=int, default=None, help="Version to rollback to")
    args = p.parse_args()
    sys.exit(main(model_dir=args.model_dir, to_version=args.to))
