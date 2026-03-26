#!/usr/bin/env python3
"""
Run the GlucoSense insulin prediction pipeline from the command line.

Executes the notebook insulin_prediction_development.ipynb end-to-end.
Requires: jupyter, nbconvert

Install deps: pip install jupyter nbconvert

Usage:
    python scripts/notebook/execute_development_notebook.py
    # Or: scripts/windows/run_pipeline.bat (Windows)
"""

import subprocess
import sys
from pathlib import Path

def main():
    root = Path(__file__).resolve().parents[2]
    notebook = root / "docs" / "notebooks" / "insulin_prediction_development.ipynb"
    
    if not notebook.exists():
        print(f"Error: Notebook not found at {notebook}")
        sys.exit(1)
    
    # EDA plots go under outputs/ (same tree as pipeline artifacts)
    (root / "outputs").mkdir(exist_ok=True)
    (root / "outputs" / "eda").mkdir(exist_ok=True)
    
    try:
        import nbconvert
    except ImportError:
        print("Missing dependency. Install with: pip install jupyter nbconvert")
        sys.exit(1)
    
    cmd = [
        sys.executable, "-m", "jupyter", "nbconvert",
        "--to", "notebook",
        "--execute",
        "--inplace",
        "--ExecutePreprocessor.timeout=600",
        str(notebook),
    ]
    
    print("Running GlucoSense pipeline...")
    print(f"Notebook: {notebook}")
    result = subprocess.run(cmd, cwd=str(root))
    
    if result.returncode == 0:
        print("\nPipeline completed successfully.")
        print(f"EDA outputs saved to: {root / 'outputs' / 'eda'}")
    else:
        print("\nPipeline failed.")
        sys.exit(result.returncode)

if __name__ == "__main__":
    main()
