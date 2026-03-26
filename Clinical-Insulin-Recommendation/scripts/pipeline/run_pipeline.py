"""
GlucoSense Full Pipeline — Single entry point for data → train → evaluate → save.

Runs the complete ML pipeline:
  1. Load and validate data
  2. EDA (optional)
  3. Clean, impute, outlier handling
  4. Feature engineering and selection
  5. 80/10/10 stratified split
  6. Train models (LogReg, DT, RF, GB, SVM)
  7. Evaluate and select best model
  8. Save best model to outputs/best_model for API inference

Usage:
  python scripts/pipeline/run_pipeline.py [--data PATH] [--no-eda] [--models NAME1 NAME2] [--out-dir DIR]

After running, start the API with: uvicorn app:app --reload --port 8000
"""
import sys

from run_evaluation import main

if __name__ == "__main__":
    sys.exit(main())
