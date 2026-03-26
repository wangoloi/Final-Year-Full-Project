"""
Train/validation/test split module.

Supports temporal split (by patient_id) and random stratified split
for model development and evaluation.
"""

import logging
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from ..config.schema import DataSchema
from ..exceptions import DataValidationError

logger = logging.getLogger(__name__)


class RandomSplitter:
    """
    Random stratified train/val/test split.
    Use for model development when temporal ordering is not required.
    """

    def __init__(
        self,
        schema: Optional[DataSchema] = None,
        train_ratio: float = 0.8,
        val_ratio: float = 0.5,
        random_state: Optional[int] = None,
    ) -> None:
        self._schema = schema or DataSchema()
        if not 0 < train_ratio < 1:
            raise DataValidationError("train_ratio must be in (0, 1)")
        if not 0 <= val_ratio <= 1:
            raise DataValidationError("val_ratio must be in [0, 1] (fraction of remainder)")
        self._train_ratio = train_ratio
        self._val_ratio = val_ratio
        self._random_state = random_state

    def split(
        self,
        df: pd.DataFrame,
        stratify_col: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split into train, validation, test by random stratified split.
        If val_ratio=0, returns (train_df, empty_df, test_df).
        """
        if df.empty:
            raise DataValidationError("Cannot split empty DataFrame.")
        stratify = df[stratify_col] if stratify_col and stratify_col in df.columns else None
        train_df, rest_df = train_test_split(
            df, train_size=self._train_ratio, stratify=stratify, random_state=self._random_state
        )
        if self._val_ratio > 0 and len(rest_df) > 0:
            stratify_rest = rest_df[stratify_col] if stratify_col and stratify_col in rest_df.columns else None
            val_df, test_df = train_test_split(
                rest_df, train_size=self._val_ratio,
                stratify=stratify_rest, random_state=self._random_state
            )
        else:
            val_df = pd.DataFrame()
            test_df = rest_df

        logger.info(
            "RandomSplitter: train=%s, val=%s, test=%s",
            len(train_df), len(val_df), len(test_df),
        )
        return train_df, val_df, test_df


class PatientSplitter:
    """
    Split by patient_id: each patient appears in only one split (train, val, or test).
    Prevents data leakage when multiple rows per patient exist.
    Stratifies by target (majority class per patient) to preserve class balance.
    """

    def __init__(
        self,
        schema: Optional[DataSchema] = None,
        train_ratio: float = 0.8,
        val_ratio: float = 0.5,
        random_state: Optional[int] = None,
    ) -> None:
        self._schema = schema or DataSchema()
        if not 0 < train_ratio < 1:
            raise DataValidationError("train_ratio must be in (0, 1)")
        if not 0 <= val_ratio <= 1:
            raise DataValidationError("val_ratio must be in [0, 1] (fraction of remainder)")
        self._train_ratio = train_ratio
        self._val_ratio = val_ratio
        self._random_state = random_state

    def split(
        self,
        df: pd.DataFrame,
        stratify_col: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split by patient: group by patient_id, assign patients to splits, return all rows.
        """
        if df.empty:
            raise DataValidationError("Cannot split empty DataFrame.")
        pid_col = self._schema.PATIENT_ID
        if pid_col not in df.columns:
            logger.warning("patient_id not in DataFrame; falling back to random split")
            from sklearn.model_selection import train_test_split
            stratify = df[stratify_col] if stratify_col and stratify_col in df.columns else None
            train_df, rest_df = train_test_split(
                df, train_size=self._train_ratio, stratify=stratify, random_state=self._random_state
            )
            if self._val_ratio > 0 and len(rest_df) > 0:
                stratify_rest = rest_df[stratify_col] if stratify_col else None
                val_df, test_df = train_test_split(
                    rest_df, train_size=self._val_ratio, stratify=stratify_rest,
                    random_state=self._random_state
                )
            else:
                val_df = pd.DataFrame()
                test_df = rest_df
            return train_df, val_df, test_df

        # Per-patient: majority target for stratification
        patient_target = df.groupby(pid_col)[stratify_col or self._schema.TARGET].agg(
            lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else x.iloc[0]
        )
        patient_ids = patient_target.index.tolist()
        stratify_vals = patient_target.values

        from sklearn.model_selection import train_test_split
        ids_train, ids_rest = train_test_split(
            patient_ids,
            train_size=self._train_ratio,
            stratify=stratify_vals,
            random_state=self._random_state,
        )
        if self._val_ratio > 0 and len(ids_rest) > 0:
            rest_targets = patient_target.loc[ids_rest].values
            ids_val, ids_test = train_test_split(
                ids_rest,
                train_size=self._val_ratio,
                stratify=rest_targets,
                random_state=self._random_state,
            )
        else:
            ids_val = []
            ids_test = ids_rest

        train_df = df[df[pid_col].isin(ids_train)]
        val_df = df[df[pid_col].isin(ids_val)] if ids_val else pd.DataFrame()
        test_df = df[df[pid_col].isin(ids_test)]

        logger.info(
            "PatientSplitter: train=%s (%s patients), val=%s (%s), test=%s (%s)",
            len(train_df), len(ids_train), len(val_df), len(ids_val), len(test_df), len(ids_test),
        )
        return train_df, val_df, test_df


class TemporalSplitter:
    """
    Splits DataFrame into train/val/test by temporal order.

    Assumes rows are ordered by time (or by patient_id as proxy).
    train_ratio of rows go to train, val_ratio of remainder to val, rest to test.
    """

    def __init__(
        self,
        schema: Optional[DataSchema] = None,
        train_ratio: float = 0.8,
        val_ratio: float = 0.5,
        random_state: Optional[int] = None,
    ) -> None:
        self._schema = schema or DataSchema()
        if not 0 < train_ratio < 1:
            raise DataValidationError("train_ratio must be in (0, 1)")
        if not 0 <= val_ratio <= 1:
            raise DataValidationError("val_ratio must be in [0, 1] (fraction of remainder)")
        self._train_ratio = train_ratio
        self._val_ratio = val_ratio
        self._random_state = random_state

    def split(
        self,
        df: pd.DataFrame,
        sort_by: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split into train, validation, test by temporal order.

        Args:
            df: Full DataFrame (will be sorted if sort_by given).
            sort_by: Column to sort by before split (e.g. patient_id). If None, uses current order.

        Returns:
            (train_df, val_df, test_df)
        """
        if df.empty:
            raise DataValidationError("Cannot split empty DataFrame.")
        data = df.sort_values(by=sort_by) if sort_by and sort_by in df.columns else df
        n = len(data)
        n_train = int(n * self._train_ratio)
        remainder = n - n_train
        n_val = int(remainder * self._val_ratio)
        n_test = remainder - n_val
        train_df = data.iloc[:n_train]
        val_df = data.iloc[n_train : n_train + n_val]
        test_df = data.iloc[n_train + n_val :]
        logger.info(
            "TemporalSplitter: train=%s, val=%s, test=%s",
            len(train_df), len(val_df), len(test_df),
        )
        return train_df, val_df, test_df
