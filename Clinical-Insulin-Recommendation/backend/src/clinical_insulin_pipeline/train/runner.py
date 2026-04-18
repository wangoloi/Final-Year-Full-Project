"""Train all models, evaluate, select best by test RMSE, export artifacts."""
from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from ..config import BUNDLE_FILENAME, OUTPUT_SUBDIR, TARGET_COL, repo_root_from_here
from ..data import prepare_dataset
from ..evaluation.export import write_evaluation_csvs
from ..evaluation.metrics import metrics_to_row, regression_metrics
from ..evaluation.shap_utils import try_shap_force_plot
from ..evaluation.visualization import (
    plot_feature_importance,
    plot_learning_curve_estimator,
    plot_residuals,
)
from ..models import build_model_factories, get_feature_importance_vector
from ..preprocessing import build_preprocessor, fit_transform_preprocessor

logger = logging.getLogger(__name__)


@dataclass
class TrainingResult:
    leaderboard: pd.DataFrame
    best_name: str
    best_model: Any
    preprocessor: Any
    feature_names: List[str]
    test_metrics: Dict[str, float]
    output_dir: Path
    per_patient_rmse: pd.DataFrame = field(default_factory=pd.DataFrame)


def _per_patient_errors(
    y_true: np.ndarray, y_pred: np.ndarray, groups: np.ndarray
) -> pd.DataFrame:
    df = pd.DataFrame({"patient": groups, "y": y_true, "p": y_pred})
    df["abs_err"] = (df["y"] - df["p"]).abs()
    df["sq_err"] = (df["y"] - df["p"]) ** 2
    g = df.groupby("patient").agg({"abs_err": "mean", "sq_err": "mean"}).reset_index()
    g["rmse"] = np.sqrt(g["sq_err"])
    return g.rename(columns={"abs_err": "mae"})


def run_training(
    csv_path: Path,
    *,
    out_dir: Path | None = None,
    skip_learning_curve: bool = False,
    skip_shap: bool = False,
) -> TrainingResult:
    repo = repo_root_from_here()
    if out_dir is None:
        out_dir = repo / OUTPUT_SUBDIR / "latest"
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    ds = prepare_dataset(csv_path)
    pre = build_preprocessor()
    raw_feature_names = list(ds.X_train.columns)
    Xtr, Xte, transformed_feature_names = fit_transform_preprocessor(pre, ds.X_train, ds.X_test)
    ytr = ds.y_train.values
    yte = ds.y_test.values

    factories = build_model_factories()
    rows: List[Dict[str, Any]] = []
    fitted: Dict[str, Any] = {}

    for name, est in factories:
        try:
            est.fit(Xtr, ytr)
            pred = est.predict(Xte)
            m = regression_metrics(yte, pred)
            rows.append(metrics_to_row(name, m))
            fitted[name] = est
            logger.info("%s test RMSE=%.4f MAE=%.4f R2=%.4f", name, m["rmse"], m["mae"], m["r2"])
        except Exception as e:
            logger.warning("Model %s failed: %s", name, e)

    if not rows:
        raise RuntimeError("No models completed successfully.")

    board = pd.DataFrame(rows)
    # Average model performance across MSE, RMSE, and R2.
    # Lower is better for MSE and RMSE; higher is better for R2.
    rank_cols = []
    for metric in ["mse", "rmse"]:
        rank_col = f"{metric}_rank"
        board[rank_col] = board[metric].rank(method="min", ascending=True)
        rank_cols.append(rank_col)
    board["r2_rank"] = board["r2"].rank(method="min", ascending=False)
    rank_cols.append("r2_rank")
    board["average_rank"] = board[rank_cols].mean(axis=1)
    board = board.sort_values(["average_rank", "rmse"]).reset_index(drop=True)
    board_path = out_dir / "leaderboard.csv"
    board.to_csv(board_path, index=False)

    best_name = str(board.iloc[0]["model"])
    logger.info(
        "Selected best model %s by average_rank=%.4f (mse=%.4f, rmse=%.4f, r2=%.4f)",
        best_name,
        board.iloc[0]["average_rank"],
        board.iloc[0]["mse"],
        board.iloc[0]["rmse"],
        board.iloc[0]["r2"],
    )
    best = fitted[best_name]
    best_pred = best.predict(Xte)
    test_metrics = regression_metrics(yte, best_pred)

    eval_dir = write_evaluation_csvs(
        out_dir,
        board,
        best_name=best_name,
        best_test_metrics=test_metrics,
        n_train=int(len(ds.y_train)),
        n_test=int(len(ds.y_test)),
        n_rows_dropped_iqr=int(ds.n_rows_dropped_iqr),
    )
    logger.info("Saved evaluation CSVs under %s", eval_dir)

    # Plots per model
    art_dir = out_dir / "models"
    art_dir.mkdir(exist_ok=True)
    for name, est in fitted.items():
        pred = est.predict(Xte)
        plot_residuals(
            yte,
            pred,
            art_dir / f"{name}_residuals.png",
            title=f"{name} test residuals",
        )
        imp = get_feature_importance_vector(est, Xtr.shape[1])
        if imp is not None and len(imp) == len(transformed_feature_names):
            plot_feature_importance(
                transformed_feature_names,
                imp,
                art_dir / f"{name}_feature_importance.png",
                title=f"{name} feature importance",
            )

    # Learning curve (best model only) — can be slow
    if not skip_learning_curve:
        try:
            plot_learning_curve_estimator(
                best,
                Xtr,
                ytr,
                art_dir / f"{best_name}_learning_curve.png",
                title=f"{best_name} learning curve",
            )
        except Exception as e:
            logger.warning("Learning curve skipped: %s", e)

    # SHAP on best model
    if not skip_shap:
        ok = try_shap_force_plot(
            best,
            Xtr,
            Xte[0:1],
            names,
            art_dir / f"{best_name}_shap_sample.png",
        )
        if not ok:
            logger.info("SHAP force plot skipped (tree/kernel explainer not available).")

    per_patient = _per_patient_errors(yte, best_pred, ds.groups_test)
    per_patient.to_csv(out_dir / "per_patient_errors_best.csv", index=False)

    meta = {
        "best_model": best_name,
        "selection_metric": "average_rank",
        "selection_detail": "average of rank positions across mse, rmse, r2",
        "test_metrics": test_metrics,
        "n_train": int(len(ds.y_train)),
        "n_test": int(len(ds.y_test)),
        "n_rows_dropped_iqr": ds.n_rows_dropped_iqr,
        "raw_feature_names": raw_feature_names,
        "transformed_feature_names": transformed_feature_names,
    }
    with open(out_dir / "run_metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    # Save bundle
    bundle = {
        "preprocessor": pre,
        "model": best,
        # Raw (pre-preprocessor) columns expected by serving/predict.py
        "feature_names": raw_feature_names,
        "raw_feature_names": raw_feature_names,
        # Transformed feature names (match estimator coefficients / importances)
        "transformed_feature_names": transformed_feature_names,
        "target_name": TARGET_COL,
        "best_model_name": best_name,
        "test_metrics": test_metrics,
    }
    import joblib

    bundle_path = out_dir / BUNDLE_FILENAME
    joblib.dump(bundle, bundle_path)

    # Deploy copy for FastAPI (outputs/best_model/inference_bundle.joblib)
    try:
        from insulin_system.persistence.bundle import (
            BUNDLE_FILENAME as API_BUNDLE_NAME,
            resolve_inference_bundle_path,
            write_deploy_metadata,
        )

        deploy_dir = repo / "outputs" / "best_model"
        deploy_dir.mkdir(parents=True, exist_ok=True)
        deploy_path = deploy_dir / API_BUNDLE_NAME
        shutil.copy2(bundle_path, deploy_path)
        write_deploy_metadata(deploy_dir, bundle)
        deployed = resolve_inference_bundle_path(None)
        if not deployed.is_file():
            raise RuntimeError(f"Expected deployed app bundle at {deployed}, but it was not found.")
        logger.info("Deployed bundle to %s", deploy_path)
    except Exception as e:
        logger.warning("Could not copy bundle to outputs/best_model: %s", e)

    return TrainingResult(
        leaderboard=board,
        best_name=best_name,
        best_model=best,
        preprocessor=pre,
        feature_names=transformed_feature_names,
        test_metrics=test_metrics,
        output_dir=out_dir,
        per_patient_rmse=per_patient,
    )
