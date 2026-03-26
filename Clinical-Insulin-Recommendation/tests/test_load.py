import pytest
from insulin_system.data_processing.load import DataLoader
from insulin_system.config.schema import DataSchema
from insulin_system.exceptions import DataValidationError

def test_loader_validate_accepts_valid_df(sample_raw_df, schema):
    loader = DataLoader(schema=schema)
    loader.validate(sample_raw_df)

def test_loader_validate_rejects_empty_df(schema):
    import pandas as pd
    loader = DataLoader(schema=schema)
    with pytest.raises(DataValidationError):
        loader.validate(pd.DataFrame())

def test_loader_validate_rejects_missing_columns(schema):
    import pandas as pd
    loader = DataLoader(schema=schema)
    df = pd.DataFrame({"age": [1], "Insulin": ["steady"]})
    with pytest.raises(DataValidationError):
        loader.validate(df)
