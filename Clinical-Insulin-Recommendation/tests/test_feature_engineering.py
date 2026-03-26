"""Tests for Feature Engineering module."""

import pytest
import pandas as pd
from insulin_system.config.schema import DataSchema, FeatureEngineeringConfig
from insulin_system.data_processing.feature_engineering import (
    FeatureEngineer,
    DERIVED_CATEGORICAL,
)
from insulin_system.data_processing.interaction_features import InteractionFeatureCreator
from insulin_system.data_processing.polynomial_features import PolynomialFeatureCreator
from insulin_system.data_processing.aggregate_features import AggregateFeatureCreator
from insulin_system.data_processing.temporal_features import TemporalFeatureCreator


def test_feature_engineer_adds_interactions_and_aggregates(sample_raw_df):
    fe = FeatureEngineer(schema=DataSchema(), config=FeatureEngineeringConfig())
    out = fe.fit_transform(sample_raw_df)
    assert "glucose_level_insulin_sensitivity_interaction" in out.columns
    assert "BMI_physical_activity_interaction" in out.columns
    assert "metabolic_risk_score" in out.columns
    assert "glycemic_burden" in out.columns
    assert "glucose_level_poly2" in out.columns
    assert "temporal_rank" in out.columns
    assert "temporal_segment" in out.columns
    assert "bmi_category" in out.columns
    assert "bmi_glucose_interaction" in out.columns


def test_derived_numeric_columns_includes_all_sources():
    cfg = FeatureEngineeringConfig()
    names = FeatureEngineer.derived_numeric_columns(cfg)
    assert "bmi_glucose_interaction" in names
    assert "weight_bmi_ratio" in names
    assert "metabolic_risk_score" in names
    assert "glycemic_burden" in names
    assert "temporal_rank" in names
    assert "glucose_level_insulin_sensitivity_interaction" in names
    assert "glucose_level_poly2" in names


def test_interaction_creator(sample_raw_df):
    creator = InteractionFeatureCreator(config=FeatureEngineeringConfig())
    out = creator.fit_transform(sample_raw_df)
    assert "glucose_level_insulin_sensitivity_interaction" in out.columns
    assert out["glucose_level_insulin_sensitivity_interaction"].iloc[0] == pytest.approx(
        sample_raw_df["glucose_level"].iloc[0] * sample_raw_df["insulin_sensitivity"].iloc[0]
    )
