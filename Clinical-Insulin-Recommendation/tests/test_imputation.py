import numpy as np
import pytest
from insulin_system.data_processing.imputation import MissingValueImputer
from insulin_system.exceptions import DataValidationError

def test_imputer_fit_transform_fills_numeric(sample_raw_df):
    df = sample_raw_df.copy()
    df.loc[0, "age"] = np.nan
    imputer = MissingValueImputer()
    out = imputer.fit_transform(df)
    assert out["age"].isna().sum() == 0

def test_imputer_transform_without_fit_raises(sample_raw_df):
    imputer = MissingValueImputer()
    with pytest.raises(DataValidationError):
        imputer.transform(sample_raw_df)
