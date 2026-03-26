"""3–4. Preprocessing: missing values, outliers, time features, categorical encoding, scaling."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_regression
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from smart_sensor_ml import config

logger = logging.getLogger(__name__)


def _hour_to_time_category(h: int) -> str:
    h = int(h) % 24
    if 5 <= h < 12:
        return "morning"
    if 12 <= h < 17:
        return "afternoon"
    if 17 <= h < 22:
        return "evening"
    return "night"


def _add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    time_col = config.COL_MEASUREMENT_TIME if config.COL_MEASUREMENT_TIME in out.columns else config.COL_TIME
    ts = pd.to_datetime(out[time_col], errors="coerce")
    hour = ts.dt.hour.fillna(0).astype(float) + ts.dt.minute.fillna(0).astype(float) / 60.0
    dow = ts.dt.dayofweek.fillna(0).astype(float)
    out["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    out["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    out["dow_sin"] = np.sin(2 * np.pi * dow / 7.0)
    out["dow_cos"] = np.cos(2 * np.pi * dow / 7.0)
    hc = ts.dt.hour.fillna(0).astype(int) % 24
    out["_time_category"] = hc.map(_hour_to_time_category)
    return out


def _add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Row-wise derived signals (no global stats — safe from label leakage)."""
    out = df.copy()
    g = pd.to_numeric(out.get("Glucose_Level"), errors="coerce")
    bmi = pd.to_numeric(out.get("BMI"), errors="coerce")
    hba1c = pd.to_numeric(out.get("HbA1c"), errors="coerce")
    hr = pd.to_numeric(out.get("Heart_Rate"), errors="coerce")
    act = pd.to_numeric(out.get("Activity_Level"), errors="coerce")
    steps = pd.to_numeric(out.get("Step_Count"), errors="coerce")
    sleep = pd.to_numeric(out.get("Sleep_Duration"), errors="coerce")
    sys = pd.to_numeric(out.get("Blood_Pressure_Systolic"), errors="coerce")
    dia = pd.to_numeric(out.get("Blood_Pressure_Diastolic"), errors="coerce")
    bmi_safe = bmi.clip(lower=0.1).fillna(26.0)
    g_safe = g.fillna(140.0)
    out["glucose_bmi_ratio"] = g_safe / bmi_safe
    out["glucose_hba1c_product"] = (g_safe * hba1c.fillna(6.5)) / 1000.0
    out["hr_glucose_ratio"] = hr.fillna(75.0) / g_safe.clip(lower=40.0)
    out["activity_glucose_interaction"] = (act.fillna(0) * g_safe) / 10000.0
    out["pulse_pressure"] = sys.fillna(120.0) - dia.fillna(80.0)
    out["steps_per_sleep_hour"] = steps.fillna(5000.0) / (sleep.fillna(6.0).clip(lower=0.25) + 0.1)
    out["map_approx"] = dia.fillna(80.0) + (sys.fillna(120.0) - dia.fillna(80.0)) / 3.0
    return out


def _add_time_since_last(df: pd.DataFrame) -> pd.DataFrame:
    """Hours since previous row per patient (§3 optional). First row per patient → 48h default."""
    out = df.copy()
    time_col = config.COL_MEASUREMENT_TIME if config.COL_MEASUREMENT_TIME in out.columns else config.COL_TIME
    out["_idx"] = np.arange(len(out))
    out["_ts"] = pd.to_datetime(out[time_col], errors="coerce")
    out = out.sort_values([config.COL_PATIENT, "_ts"])
    prev = out.groupby(config.COL_PATIENT)["_ts"].shift(1)
    out["time_since_last_hours"] = (
        (out["_ts"] - prev).dt.total_seconds() / 3600.0
    ).fillna(48.0).clip(0.0, 168.0)
    out = out.sort_values("_idx").drop(columns=["_idx", "_ts"])
    return out


def _iqr_clip_series(s: pd.Series, train_s: pd.Series, factor: float = 1.5) -> pd.Series:
    q1, q3 = train_s.quantile(0.25), train_s.quantile(0.75)
    iqr = q3 - q1
    lo, hi = q1 - factor * iqr, q3 + factor * iqr
    return s.clip(lower=lo, upper=hi)


def build_insulin_tier_labels(
    insulin_values: pd.Series, bin_edges: Optional[np.ndarray] = None
) -> Tuple[pd.Series, np.ndarray]:
    """
    Ordinal 3-class target from Insulin_Dose using train-derived tertile edges (§5).
    """
    v = pd.to_numeric(insulin_values, errors="coerce")
    if bin_edges is None:
        valid = v.dropna()
        if len(valid) < 30:
            raise ValueError("Not enough non-null Insulin_Dose rows to form tiers.")
        try:
            _, bin_edges = pd.qcut(valid, q=config.N_CLASSES, retbins=True, duplicates="drop")
        except ValueError:
            _, bin_edges = pd.qcut(valid.rank(method="first"), q=config.N_CLASSES, retbins=True, duplicates="drop")
        if len(bin_edges) - 1 < config.N_CLASSES:
            qs = valid.quantile([0, 1 / 3, 2 / 3, 1.0]).values.astype(float)
            bin_edges = np.unique(qs)
    cats = pd.cut(v, bins=bin_edges, labels=False, include_lowest=True)
    y = cats.astype("float").fillna(-1).astype(int)
    y = y.where(y >= 0, 1)
    y = y.clip(0, config.N_CLASSES - 1)
    return y, np.asarray(bin_edges)


def insulin_dose_to_tier_name(dose: float, bin_edges: Optional[np.ndarray]) -> Tuple[int, str]:
    """Map predicted continuous dose to Low / Moderate / High using train-derived tertile edges."""
    if bin_edges is None or dose != dose:
        return 1, str(config.CLASS_NAMES[1])
    v = pd.Series([float(dose)])
    cats = pd.cut(v, bins=bin_edges, labels=False, include_lowest=True)
    idx = cats.iloc[0]
    if pd.isna(idx):
        idx = 1
    idx = int(np.clip(int(idx), 0, config.N_CLASSES - 1))
    return idx, str(config.CLASS_NAMES[idx])


@dataclass
class PreprocessPipeline:
    """Fit on training DataFrame only; transform train/val/test consistently (§4, §11)."""

    numeric_cols: List[str] = field(
        default_factory=lambda: list(config.NUMERIC_FEATURES) + list(config.DERIVED_FEATURE_NAMES)
    )
    time_cyclical_cols: Tuple[str, ...] = ("hour_sin", "hour_cos", "dow_sin", "dow_cos")
    extra_numeric_cols: Tuple[str, ...] = ("time_since_last_hours",)
    imputer: Optional[SimpleImputer] = None
    scaler: Optional[StandardScaler] = None
    patient_encoder: Optional[OrdinalEncoder] = None
    meal_encoder: Optional[OneHotEncoder] = None
    activity_encoder: Optional[OneHotEncoder] = None
    time_cat_encoder: Optional[OneHotEncoder] = None
    insulin_bin_edges: Optional[np.ndarray] = None
    selected_features: List[str] = field(default_factory=list)
    drop_features: List[str] = field(default_factory=list)
    _train_clip_bounds: dict = field(default_factory=dict)
    _meal_feature_names: List[str] = field(default_factory=list)
    _activity_feature_names: List[str] = field(default_factory=list)
    _timecat_feature_names: List[str] = field(default_factory=list)
    mi_kept_columns: List[str] = field(default_factory=list)
    _imputer_columns: List[str] = field(default_factory=list)
    mi_ranked_final: List[str] = field(default_factory=list)
    mi_scores_map: dict = field(default_factory=dict)
    active_feature_count: int = 0

    def _feature_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        df2 = _add_time_features(df)
        df2 = _add_time_since_last(df2)
        df2 = _add_derived_features(df2)
        pid = df2[[config.COL_PATIENT]].astype(str)
        pid_enc = self.patient_encoder.transform(pid)

        Xnum = df2[list(self.numeric_cols) + list(self.time_cyclical_cols) + list(self.extra_numeric_cols)].copy()
        for c in self.numeric_cols:
            if c in Xnum.columns:
                Xnum[c] = pd.to_numeric(Xnum[c], errors="coerce")

        parts = [Xnum, pd.DataFrame({"patient_enc": pid_enc.ravel()}, index=df2.index)]

        if self.meal_encoder is not None:
            m = self.meal_encoder.transform(df2[[config.COL_MEAL_CONTEXT]].astype(str))
            parts.append(pd.DataFrame(m, columns=self._meal_feature_names, index=df2.index))
        if self.activity_encoder is not None:
            a = self.activity_encoder.transform(df2[[config.COL_ACTIVITY_CONTEXT]].astype(str))
            parts.append(pd.DataFrame(a, columns=self._activity_feature_names, index=df2.index))
        if self.time_cat_encoder is not None:
            tc = df2["_time_category"].astype(str).to_frame(name="_time_category")
            t = self.time_cat_encoder.transform(tc)
            parts.append(pd.DataFrame(t, columns=self._timecat_feature_names, index=df2.index))

        X = pd.concat(parts, axis=1)
        return X

    def fit(self, df_train: pd.DataFrame) -> "PreprocessPipeline":
        df_train = df_train.copy()
        self.patient_encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
        self.patient_encoder.fit(df_train[[config.COL_PATIENT]].astype(str))

        self.meal_encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        self.meal_encoder.fit(df_train[[config.COL_MEAL_CONTEXT]].astype(str))
        self._meal_feature_names = list(self.meal_encoder.get_feature_names_out([config.COL_MEAL_CONTEXT]))

        self.activity_encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        self.activity_encoder.fit(df_train[[config.COL_ACTIVITY_CONTEXT]].astype(str))
        self._activity_feature_names = list(self.activity_encoder.get_feature_names_out([config.COL_ACTIVITY_CONTEXT]))

        df_tc = _add_time_features(df_train)
        self.time_cat_encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        self.time_cat_encoder.fit(df_tc[["_time_category"]].astype(str))
        self._timecat_feature_names = list(self.time_cat_encoder.get_feature_names_out(["_time_category"]))

        # Tier edges (train quantiles) for downstream dose → Low/Moderate/High; MI uses continuous target
        _, self.insulin_bin_edges = build_insulin_tier_labels(df_train[config.COL_TARGET])

        X_train = self._feature_matrix(df_train)
        self._train_clip_bounds = {}
        for c in list(self.numeric_cols) + list(self.extra_numeric_cols):
            if c not in X_train.columns:
                continue
            s = X_train[c]
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            self._train_clip_bounds[c] = (float(q1 - 1.5 * iqr), float(q3 + 1.5 * iqr))
            X_train[c] = _iqr_clip_series(s, s)

        self.imputer = SimpleImputer(strategy="median")
        self.imputer.fit(X_train)
        self._imputer_columns = list(X_train.columns)
        X_imp = pd.DataFrame(self.imputer.transform(X_train), columns=self._imputer_columns, index=X_train.index)

        y_cont = pd.to_numeric(df_train[config.COL_TARGET], errors="coerce")
        valid = y_cont.notna()
        if valid.sum() < 30:
            raise ValueError("Not enough non-null Insulin_Dose rows for mutual information (regression).")
        X_mi = X_imp.loc[valid].values
        y_mi = y_cont.loc[valid].values.astype(float)
        mi_scores = mutual_info_regression(X_mi, y_mi, random_state=config.RANDOM_STATE)
        cols = list(X_imp.columns)
        self.mi_scores_map = {cols[i]: float(mi_scores[i]) for i in range(len(cols))}
        order_full = np.argsort(mi_scores)[::-1]
        pool_n = min(config.MI_MAX_POOL_FOR_CORR, len(cols))
        pool_cols = [cols[i] for i in order_full[:pool_n]]
        X_pool = X_imp[pool_cols]

        corr = X_pool.corr().abs()
        upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
        to_drop = [c for c in upper.columns if any(upper[c] > 0.95)]
        self.drop_features = to_drop
        remaining = [c for c in pool_cols if c not in to_drop]
        self.mi_ranked_final = sorted(remaining, key=lambda c: self.mi_scores_map.get(c, 0.0), reverse=True)
        self.mi_kept_columns = list(self.mi_ranked_final)
        logger.info(
            "MI ranking + correlation: %s candidate features (train-only, dropped corr>0.95: %s)",
            len(self.mi_ranked_final),
            to_drop,
        )
        return self

    def select_top_n(self, n: int, df_train: pd.DataFrame) -> None:
        """Subset to top-N MI-ranked features (after correlation filter) and fit StandardScaler on train only."""
        if not self.mi_ranked_final or self.imputer is None:
            raise RuntimeError("Call fit() before select_top_n.")
        n = min(int(n), len(self.mi_ranked_final))
        n = max(1, n)
        if len(self.mi_ranked_final) >= config.MI_MIN_FEATURES:
            n = max(config.MI_MIN_FEATURES, n)
        self.selected_features = self.mi_ranked_final[:n]
        self.active_feature_count = len(self.selected_features)
        X_train = self._feature_matrix(df_train)
        for c, (lo, hi) in self._train_clip_bounds.items():
            if c in X_train.columns:
                X_train[c] = X_train[c].clip(lower=lo, upper=hi)
        X_imp_full = pd.DataFrame(self.imputer.transform(X_train), columns=self._imputer_columns, index=X_train.index)
        for col in self.mi_ranked_final:
            if col not in X_imp_full.columns:
                X_imp_full[col] = 0.0
        X_sub = X_imp_full[self.selected_features]
        self.scaler = StandardScaler()
        self.scaler.fit(X_sub.values)
        logger.info("select_top_n(%s): scaler fit on %s features", n, len(self.selected_features))

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        if self.imputer is None or self.scaler is None or self.patient_encoder is None:
            raise RuntimeError("Call fit() first.")
        if not self.selected_features:
            raise RuntimeError("No selected_features — call fit() or select_top_n().")
        X = self._feature_matrix(df)
        for c, (lo, hi) in self._train_clip_bounds.items():
            if c in X.columns:
                X[c] = X[c].clip(lower=lo, upper=hi)
        X_imp_full = pd.DataFrame(self.imputer.transform(X), columns=self._imputer_columns, index=X.index)
        for col in self.mi_ranked_final:
            if col not in X_imp_full.columns:
                X_imp_full[col] = 0.0
        X_sub = X_imp_full[self.selected_features]
        return self.scaler.transform(X_sub.values)


def preprocess_data(
    df_train: pd.DataFrame,
    df_other: Optional[pd.DataFrame] = None,
) -> Tuple[PreprocessPipeline, Optional[np.ndarray]]:
    pipe = PreprocessPipeline()
    pipe.fit(df_train)
    pipe.select_top_n(len(pipe.mi_ranked_final), df_train)
    other_arr = pipe.transform(df_other) if df_other is not None else None
    return pipe, other_arr
