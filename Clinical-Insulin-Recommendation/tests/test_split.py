import pandas as pd
import pytest
from insulin_system.data_processing.split import TemporalSplitter
from insulin_system.exceptions import DataValidationError

def test_split_sizes(sample_raw_df):
    splitter = TemporalSplitter(train_ratio=0.6, val_ratio=0.2)
    train, val, test = splitter.split(sample_raw_df)
    assert len(train) + len(val) + len(test) == len(sample_raw_df)

def test_split_empty_raises():
    splitter = TemporalSplitter(train_ratio=0.7, val_ratio=0.15)
    with pytest.raises(DataValidationError):
        splitter.split(pd.DataFrame())
