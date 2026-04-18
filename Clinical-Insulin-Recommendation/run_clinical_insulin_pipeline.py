from __future__ import annotations

import logging
import sys
from pathlib import Path


def _ensure_backend_src_on_path() -> None:
    repo_root = Path(__file__).resolve().parent
    backend_src = repo_root / "backend" / "src"
    if not backend_src.is_dir():
        raise RuntimeError(f"Expected backend/src at: {backend_src}")
    sys.path.insert(0, str(backend_src))


def main(argv: list[str] | None = None) -> int:
    _ensure_backend_src_on_path()
    from clinical_insulin_pipeline.train.cli import main as pipeline_main

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    return pipeline_main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
