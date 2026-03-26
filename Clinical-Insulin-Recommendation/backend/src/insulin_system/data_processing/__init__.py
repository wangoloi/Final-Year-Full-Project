"""
Data processing pipeline for insulin dosage prediction.

Components:
- load: Load and validate raw CSV data
- eda: Exploratory data analysis and visualizations
- imputation: Missing value handling
- outliers: Outlier detection and handling with clinical validation
- feature_engineering: Derived, interaction, polynomial, aggregate, temporal features
- encoding: Categorical encoding
- scaling: Feature scaling
- feature_selection: Domain + statistical feature selection
- split: Temporal train/val/test split
- pipeline: Orchestrated end-to-end pipeline
"""

from .load import DataLoader, load_and_validate
from .pipeline import DataProcessingPipeline, PipelineResult
from .feature_engineering import FeatureEngineer, DERIVED_CATEGORICAL
from .feature_selection import FeatureSelector

__all__ = [
    "DataLoader",
    "load_and_validate",
    "DataProcessingPipeline",
    "PipelineResult",
    "FeatureEngineer",
    "DERIVED_CATEGORICAL",
    "FeatureSelector",
]
