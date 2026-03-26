"""
ML Pipeline Configuration.

Centralizes all configuration for the machine learning pipeline:
data loading, preprocessing, feature engineering, model training, evaluation, and visualization.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class DataConfig:
    """Data loading and validation configuration."""

    patient_id_col: str = "patient_id"
    target_col: str = "Insulin"
    target_regression_col: str = "Insulin_Dose"
    categorical_cols: Tuple[str, ...] = ("gender", "family_history", "food_intake", "previous_medications")
    numeric_cols: Tuple[str, ...] = (
        "age", "glucose_level", "physical_activity", "BMI", "HbA1c",
        "weight", "insulin_sensitivity", "sleep_hours", "creatinine",
    )
    contextual_cols: Tuple[str, ...] = ("iob", "anticipated_carbs", "glucose_trend_encoded")
    contextual_impute: Tuple[str, ...] = ("iob", "anticipated_carbs")
    random_state: int = 42


@dataclass
class PreprocessingConfig:
    """Preprocessing pipeline configuration."""

    split_type: str = "temporal"  # "temporal" | "random"
    train_ratio: float = 0.8
    val_ratio: float = 0.5
    outlier_strategy: str = "clip"  # clip | remove | flag
    scaler_type: str = "standard"  # standard | minmax | robust
    missing_numeric_strategy: str = "median"
    missing_categorical_strategy: str = "mode"
    random_state: int = 42


@dataclass
class FeatureConfig:
    """Feature engineering configuration."""

    interaction_pairs: Tuple[Tuple[str, str], ...] = (
        ("glucose_level", "insulin_sensitivity"),
        ("BMI", "physical_activity"),
        ("HbA1c", "glucose_level"),
        ("weight", "insulin_sensitivity"),
        ("age", "BMI"),
        ("iob", "anticipated_carbs"),  # NEW: contextual interaction
    )
    polynomial_columns: Tuple[str, ...] = ("glucose_level", "HbA1c", "BMI", "insulin_sensitivity")
    polynomial_degree: int = 2
    selection_method: str = "mutual_info"  # mutual_info | f_classif | rfe | none
    selection_k: Optional[int] = 35  # Increased from 30 for more feature retention
    variance_threshold: float = 1e-5
    domain_keep: Tuple[str, ...] = (
        "glucose_level", "HbA1c", "BMI", "insulin_sensitivity", "age",
        "physical_activity", "iob", "anticipated_carbs", "glucose_trend_encoded",
        "glucose_zone_numeric",
    )
    temporal_order_column: Optional[str] = "patient_id"
    random_state: int = 42


@dataclass
class ClassBalanceConfig:
    """Class imbalance handling configuration."""

    strategy: str = "class_weight"  # class_weight | smote | smote_tomek | none
    smote_k_neighbors: int = 5
    minority_class_weight_multiplier: float = 2.5  # Increased from 2.0
    minority_classes: Tuple[str, ...] = ("down", "no")
    random_state: int = 42


@dataclass
class TuningConfig:
    """Hyperparameter tuning configuration."""

    search_type: str = "random"  # grid | random | optuna
    cv_folds: int = 5
    random_search_n_iter: int = 50  # Increased from 30
    optuna_n_trials: int = 50
    optuna_timeout: Optional[float] = 300.0  # seconds
    scoring: str = "f1_weighted"
    stratify_cv: bool = True
    n_jobs: int = -1
    random_state: int = 42


@dataclass
class EvaluationConfig:
    """Evaluation and output configuration."""

    output_dir: Path = field(default_factory=lambda: Path("outputs/evaluation"))
    plot_confusion_matrix: bool = True
    plot_roc_auc: bool = True
    plot_calibration: bool = True
    plot_learning_curve: bool = True
    plot_feature_importance: bool = True
    plot_class_distribution: bool = True
    plot_model_comparison: bool = True
    learning_curve_train_sizes: Tuple[float, ...] = (0.1, 0.3, 0.5, 0.7, 1.0)
    permutation_repeats: int = 10
    temporal_segment_column: str = "temporal_segment"
    use_clinical_cost: bool = True


@dataclass
class MLPipelineConfig:
    """Master configuration for the full ML pipeline."""

    data: DataConfig = field(default_factory=DataConfig)
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    class_balance: ClassBalanceConfig = field(default_factory=ClassBalanceConfig)
    tuning: TuningConfig = field(default_factory=TuningConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)

    # Model selection
    models: Tuple[str, ...] = (
        "logistic_regression", "decision_tree", "random_forest",
        "gradient_boosting",
    )
    use_stacking: bool = True
    exclude_mlp: bool = True
    exclude_rnn: bool = True
