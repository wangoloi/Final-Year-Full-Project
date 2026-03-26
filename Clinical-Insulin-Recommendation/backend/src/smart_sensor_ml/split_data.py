"""Stratified group splits: 70% train / 10% validation / 20% test (no patient leakage)."""
from __future__ import annotations

import logging
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from smart_sensor_ml import config

logger = logging.getLogger(__name__)


def stratified_group_train_val_test(
    df: pd.DataFrame,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split rows into train/val/test with proportions ~70% / 10% / 20% by **patient**.

    Stratification uses each patient's **median insulin dose** binned into quantile groups
    so class balance is roughly preserved across splits (patient-level proxy).
    """
    gc = config.COL_PATIENT
    tc = config.COL_TARGET
    gstats = df.groupby(gc, sort=False)[tc].median()
    patients = gstats.index.astype(str).values
    med = gstats.values.astype(float)
    n_pat = len(patients)
    if n_pat < 6:
        raise ValueError("Need at least 6 distinct patients for a 70/10/20 split.")

    try:
        n_bins = min(3, len(np.unique(med)))
        strat = pd.qcut(pd.Series(med).rank(method="first"), q=n_bins, labels=False, duplicates="drop")
        strat = np.asarray(strat, dtype=int)
    except Exception:
        strat = np.zeros(n_pat, dtype=int)

    try:
        trv_p, te_p = train_test_split(patients, test_size=0.20, stratify=strat, random_state=random_state)
        strat_trv = pd.Series(strat, index=patients).loc[trv_p].values
        tr_p, va_p = train_test_split(trv_p, test_size=0.125, stratify=strat_trv, random_state=random_state)
    except ValueError:
        trv_p, te_p = train_test_split(patients, test_size=0.20, random_state=random_state)
        tr_p, va_p = train_test_split(trv_p, test_size=0.125, random_state=random_state)

    train_df = df[df[gc].astype(str).isin(set(tr_p))].reset_index(drop=True)
    val_df = df[df[gc].astype(str).isin(set(va_p))].reset_index(drop=True)
    test_df = df[df[gc].astype(str).isin(set(te_p))].reset_index(drop=True)

    n_total = len(df)
    logger.info(
        "Split 70/10/20 (by patient): train=%s rows (%.1f%%), val=%s (%.1f%%), test=%s (%.1f%%) | "
        "patients train=%s val=%s test=%s",
        len(train_df),
        100 * len(train_df) / n_total,
        len(val_df),
        100 * len(val_df) / n_total,
        len(test_df),
        100 * len(test_df) / n_total,
        len(tr_p),
        len(va_p),
        len(te_p),
    )
    return train_df, val_df, test_df
