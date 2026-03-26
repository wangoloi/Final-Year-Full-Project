"""
Orchestrated data processing pipeline.

Runs load -> EDA (optional) -> impute -> outliers -> feature_engineering
-> encode -> scale -> temporal split. Exposes a single entry point and
returns train/val/test DataFrames plus fitted components for reuse.
"""

import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Tuple

import pandas as pd

from ..config.schema import (
    DataSchema,
    ClinicalBounds,
    EDAPathConfig,
    FeatureEngineeringConfig,
    PipelineConfig,
)
from ..exceptions import DataLoadError, DataValidationError, PipelineError
from .load import DataLoader, derive_insulin_dose
from .eda import EDAAnalyzer
from .imputation import MissingValueImputer
from .outliers import OutlierHandler
from .feature_engineering import FeatureEngineer, DERIVED_CATEGORICAL
from .encoding import CategoricalEncoder
from .scaling import FeatureScaler
from .split import TemporalSplitter, RandomSplitter, PatientSplitter
from .feature_selection import FeatureSelector

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of running the data processing pipeline."""

    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame
    X_train: pd.DataFrame
    X_val: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_val: pd.Series
    y_test: pd.Series
    feature_names: list = field(default_factory=list)
    imputer: Optional[MissingValueImputer] = None
    encoder: Optional[CategoricalEncoder] = None
    scaler: Optional[FeatureScaler] = None
    feature_selector: Optional[FeatureSelector] = None
    outlier_handler: Optional[OutlierHandler] = None
    feature_engineer: Optional[FeatureEngineer] = None
    eda_path: Optional[str] = None


class DataProcessingPipeline:
    """
    End-to-end data processing with temporal split.
    All steps are configurable and testable via dependency injection.
    """

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        schema: Optional[DataSchema] = None,
        data_path: Optional[Path] = None,
    ) -> None:
        self._config = config or PipelineConfig()
        self._schema = schema or DataSchema()
        self._data_path = data_path
        self._loader = DataLoader(schema=self._schema, file_path=data_path)
        self._eda = EDAAnalyzer(schema=self._schema)
        self._imputer = MissingValueImputer(
            schema=self._schema,
            numeric_strategy=self._config.missing_numeric_strategy,
            categorical_strategy=self._config.missing_categorical_strategy,
        )
        self._outlier_handler = OutlierHandler(
            schema=self._schema,
            bounds=ClinicalBounds(),
            strategy=self._config.outlier_strategy,
        )
        fe_config = FeatureEngineeringConfig()
        self._feature_engineer = FeatureEngineer(schema=self._schema, config=fe_config)
        self._fe_config = fe_config
        self._encoder = CategoricalEncoder(
            schema=self._schema,
            drop_first=True,
            extra_categorical_columns=DERIVED_CATEGORICAL,
        )
        self._scaler = FeatureScaler(
            schema=self._schema,
            scaler_type=self._config.scaler_type,
            extra_numeric_columns=FeatureEngineer.derived_numeric_columns(fe_config),
        )
        self._feature_selector = FeatureSelector(config=fe_config)
        split_type = getattr(self._config, "split_type", "temporal")
        if split_type == "random":
            self._splitter = RandomSplitter(
                schema=self._schema,
                train_ratio=self._config.train_ratio,
                val_ratio=getattr(self._config, "val_ratio", 0.0),
                random_state=self._config.random_state,
            )
        elif split_type == "patient":
            self._splitter = PatientSplitter(
                schema=self._schema,
                train_ratio=self._config.train_ratio,
                val_ratio=getattr(self._config, "val_ratio", 0.5),
                random_state=self._config.random_state,
            )
        else:
            self._splitter = TemporalSplitter(
                schema=self._schema,
                train_ratio=self._config.train_ratio,
                val_ratio=self._config.val_ratio,
                random_state=self._config.random_state,
            )

    def run(
        self,
        data_path: Optional[Path] = None,
        run_eda: bool = True,
        eda_output_dir: Optional[Path] = None,
        run_feature_selection: bool = True,
    ) -> PipelineResult:
        """
        Load data, run EDA (optional), preprocess, and split.

        Returns:
            PipelineResult with train/val/test and fitted components.
        """
        path = data_path or self._data_path
        if path is None:
            raise PipelineError("No data path provided.")
        path = Path(path)

        df = self._loader.load_and_validate(path)
        if self._config.regression_mode:
            df = derive_insulin_dose(df, self._schema)
        eda_path = None
        if run_eda:
            eda_path = self._eda.run(df, output_dir=eda_output_dir)
            logger.info("EDA written to %s", eda_path)

        df = self._imputer.fit_transform(df)
        df = self._outlier_handler.fit_transform(df)
        df = self._feature_engineer.fit_transform(df)
        df = self._encoder.fit_transform(df)
        df = self._scaler.fit_transform(df)

        target_col = self._schema.TARGET_REGRESSION if self._config.regression_mode else self._schema.TARGET
        if isinstance(self._splitter, RandomSplitter):
            stratify_col = None if self._config.regression_mode else self._schema.TARGET
            train_df, val_df, test_df = self._splitter.split(df, stratify_col=stratify_col)
        elif isinstance(self._splitter, PatientSplitter):
            stratify_col = None if self._config.regression_mode else self._schema.TARGET
            train_df, val_df, test_df = self._splitter.split(df, stratify_col=stratify_col)
        else:
            train_df, val_df, test_df = self._splitter.split(df, sort_by=self._schema.PATIENT_ID)

        def get_X_y(data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
            exclude = {self._schema.PATIENT_ID, self._schema.TARGET, self._schema.TARGET_REGRESSION, "_outlier_flag"}
            feat_cols = [c for c in data.columns if c not in exclude]
            X = data[feat_cols]
            y = data[target_col]
            return X, y

        X_train, y_train = get_X_y(train_df)
        X_val, y_val = get_X_y(val_df)
        X_test, y_test = get_X_y(test_df)
        feature_names = list(X_train.columns)

        if run_feature_selection and self._fe_config.SELECTION_METHOD != "none":
            self._feature_selector.fit(X_train, y_train)
            X_train = self._feature_selector.transform(X_train)
            X_val = self._feature_selector.transform(X_val)
            X_test = self._feature_selector.transform(X_test)
            feature_names = self._feature_selector.selected_features
            logger.info("Feature selection: %s features", len(feature_names))

        return PipelineResult(
            train=train_df,
            val=val_df,
            test=test_df,
            X_train=X_train,
            X_val=X_val,
            X_test=X_test,
            y_train=y_train,
            y_val=y_val,
            y_test=y_test,
            feature_names=feature_names,
            imputer=self._imputer,
            encoder=self._encoder,
            scaler=self._scaler,
            feature_selector=self._feature_selector if run_feature_selection else None,
            outlier_handler=self._outlier_handler,
            feature_engineer=self._feature_engineer,
            eda_path=eda_path,
        )
