"""
Clinical insulin dose regression pipeline.

Layout:
  data/          — CSV loading, engineered features, splits
  preprocessing/ — imputation + scaling
  models/        — regression model zoo
  evaluation/    — metrics, plots, SHAP helpers
  serving/       — inference schema + prediction
  train/         — training loop and CLI
  config.py      — paths and hyperparameter defaults
"""
__version__ = "1.0.0"
