import pytest
from insulin_system.config.schema import ClinicalBounds, DataSchema
from insulin_system.data_processing.outliers import OutlierHandler
from insulin_system.exceptions import DataValidationError

def test_outlier_handler_clip_bounds(sample_raw_df):
    df = sample_raw_df.copy()
    df.loc[0, "age"] = 200.0
    handler = OutlierHandler(schema=DataSchema(), bounds=ClinicalBounds(), strategy="clip")
    out = handler.fit_transform(df)
    assert out.loc[0, "age"] == 120.0

def test_outlier_handler_invalid_strategy_raises():
    with pytest.raises(DataValidationError):
        OutlierHandler(strategy="invalid")
