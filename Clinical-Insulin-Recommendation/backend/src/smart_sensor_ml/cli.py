"""CLI — run full pipeline, write artifacts + PDF (insulin dose regression)."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from smart_sensor_ml import config
from smart_sensor_ml.eda_analysis import plot_eda_figures, run_full_eda
from smart_sensor_ml.evaluation_report import (
    best_model_metrics_nested,
    build_evaluation_report,
    enrich_comparison_with_generalized_score,
    write_evaluation_report,
)
from smart_sensor_ml.evaluate_model import cross_validate_groups_regression, evaluate_regression_model
from smart_sensor_ml.feature_selection import select_best_feature_count
from smart_sensor_ml.split_data import stratified_group_train_val_test
from smart_sensor_ml.load_data import enrich_training_dataframe, exploratory_summary, load_data, print_exploratory
from smart_sensor_ml.persistence import ProductionBundle, predict_new_data, save_model
from smart_sensor_ml.plots import (
    plot_feature_importance,
    plot_pred_vs_actual,
    plot_regression_residuals,
    plot_target_and_glucose_distributions,
)
from smart_sensor_ml.preprocess import PreprocessPipeline
from smart_sensor_ml.report_pdf import build_pdf_report
from smart_sensor_ml.tuning import train_tune_all_regression
from smart_sensor_ml.validate_data import validate_data

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_pipeline(
    data_path: Path,
    out_dir: Path,
    skip_lstm: bool = True,
    random_state: int = 42,
) -> None:
    out_dir = Path(out_dir)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    np.random.seed(random_state)

    df = load_data(data_path)
    df = enrich_training_dataframe(df)
    df, val_msgs = validate_data(df)
    eda = exploratory_summary(df)
    print_exploratory(eda)
    with open(out_dir / "validation_warnings.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(val_msgs) or "No validation warnings.")

    run_full_eda(df, out_dir)
    plot_eda_figures(df, out_dir)
    plot_target_and_glucose_distributions(df, fig_dir)

    train_df, val_df, test_df = stratified_group_train_val_test(df, random_state=random_state)

    pre = PreprocessPipeline()
    pre.fit(train_df)

    best_n, probe_rows = select_best_feature_count(pre, train_df, val_df, random_state=random_state)
    pd.DataFrame(probe_rows).to_csv(out_dir / "feature_count_probe.csv", index=False)

    pre.select_top_n(best_n, train_df)
    X_train = pre.transform(train_df)
    X_val = pre.transform(val_df)
    X_test = pre.transform(test_df)

    y_train = pd.to_numeric(train_df[config.COL_TARGET], errors="coerce").values.astype(float)
    y_val = pd.to_numeric(val_df[config.COL_TARGET], errors="coerce").values.astype(float)
    y_test = pd.to_numeric(test_df[config.COL_TARGET], errors="coerce").values.astype(float)

    groups_tr = train_df[config.COL_PATIENT].astype(str).values
    logger.info(
        "Hyperparameter search: %s iterations, %s-fold grouped CV (regression)",
        config.TUNING_N_ITER,
        config.TUNING_CV_FOLDS,
    )
    fitted = train_tune_all_regression(X_train, y_train, groups_tr, random_state=random_state)

    n_groups = len(np.unique(groups_tr))
    cv_splits = min(config.CV_FOLDS, max(2, n_groups // 2))
    cv_rows = []
    cv_by_model: dict = {}

    rows = []
    for name, model in fitted.items():
        ev_tr = evaluate_regression_model(model, X_train, y_train, model_name=name)
        ev_va = evaluate_regression_model(
            model, X_val, y_val, model_name=name, X_train=X_train, y_train=y_train
        )
        ev_te = evaluate_regression_model(
            model, X_test, y_test, model_name=name, X_train=X_train, y_train=y_train
        )
        try:
            cv = cross_validate_groups_regression(
                model, X_train, y_train, groups_tr, n_splits=cv_splits, random_state=random_state
            )
        except Exception as e:
            logger.warning("CV failed for %s: %s", name, e)
            cv = {}
        cv_by_model[name] = cv
        cv_rows.append({"model": name, **cv})
        gap_tv = float(ev_tr.r2) - float(ev_va.r2)
        gap_rmse = float(ev_tr.rmse) - float(ev_va.rmse)
        rows.append(
            {
                "model": name,
                "train_r2": ev_tr.r2,
                "val_r2": ev_va.r2,
                "test_r2": ev_te.r2,
                "train_rmse": ev_tr.rmse,
                "val_rmse": ev_va.rmse,
                "test_rmse": ev_te.rmse,
                "train_mae": ev_tr.mae,
                "val_mae": ev_va.mae,
                "test_mae": ev_te.mae,
                "train_val_gap_r2": gap_tv,
                "train_val_gap_rmse": gap_rmse,
                "overfit_gap_r2_train_val": ev_va.overfit_gap_r2,
            }
        )
        logger.info(
            "%s — train R²=%.4f val R²=%.4f test R²=%.4f | val RMSE=%.4f test RMSE=%.4f",
            name,
            ev_tr.r2,
            ev_va.r2,
            ev_te.r2,
            ev_va.rmse,
            ev_te.rmse,
        )
        y_pred_te = model.predict(X_test)
        plot_regression_residuals(
            y_test,
            y_pred_te,
            fig_dir / f"residuals_{name}.png",
            title=f"Residuals — {name} (test)",
        )
        plot_pred_vs_actual(y_test, y_pred_te, fig_dir / f"pred_vs_actual_{name}.png")
        if hasattr(model, "feature_importances_"):
            plot_feature_importance(
                np.asarray(model.feature_importances_),
                pre.selected_features,
                fig_dir / f"importance_{name}.png",
                title=f"Importance — {name}",
            )

    comp = pd.DataFrame(rows)
    comp_enriched = enrich_comparison_with_generalized_score(comp)
    comp_enriched.to_csv(out_dir / "model_comparison.csv", index=False)
    pd.DataFrame(cv_rows).to_csv(out_dir / "cv_summary.csv", index=False)

    _MAX_ACCEPTABLE_R2_GAP = 0.35
    _cand = comp[comp["overfit_gap_r2_train_val"] <= _MAX_ACCEPTABLE_R2_GAP].copy()
    if len(_cand) > 0:
        comp_for_pick = _cand.sort_values(["val_r2", "val_rmse"], ascending=[False, True]).reset_index(drop=True)
        logger.info(
            "Model shortlist: train–val R² gap ≤ %.2f (%s candidates); selection by **validation** R².",
            _MAX_ACCEPTABLE_R2_GAP,
            len(comp_for_pick),
        )
    else:
        comp_for_pick = comp.sort_values(["val_r2"], ascending=False).reset_index(drop=True)
        logger.warning("All models exceed R² gap %.2f on val; selecting by validation R² anyway.", _MAX_ACCEPTABLE_R2_GAP)

    best_row = comp_for_pick.iloc[0]
    best_name = str(best_row["model"])
    rationale_extra = ""

    if len(comp_for_pick) > 1:
        second = comp_for_pick.iloc[1]
        d = float(best_row["val_r2"]) - float(second["val_r2"])
        s0 = cv_by_model.get(best_name, {}).get("cv_r2_std", 0.0)
        s1 = cv_by_model.get(str(second["model"]), {}).get("cv_r2_std", 0.0)
        g0 = float(best_row["overfit_gap_r2_train_val"])
        g1 = float(second["overfit_gap_r2_train_val"])
        if d <= config.COMPOSITE_TIE_THRESHOLD and d < 0.003:
            pick_second = False
            if s1 < s0 - 1e-6:
                pick_second = True
                rationale_extra = f"Tie-break: {second['model']} has lower CV R² std ({s1:.4f} vs {s0:.4f})."
            elif abs(s1 - s0) < 1e-6 and g1 < g0 - 1e-6:
                pick_second = True
                rationale_extra = f"Tie-break: {second['model']} has smaller train–val R² gap ({g1:.4f} vs {g0:.4f})."
            if pick_second:
                best_name = str(second["model"])
                best_row = second

    best_model = fitted[best_name]
    best_row_gs = comp_enriched[comp_enriched["model"] == best_name].iloc[0]
    repo_root = Path(__file__).resolve().parents[3]
    selection_rule = (
        "Shortlist models with train–val R² gap ≤ 0.35 (overfitting guard); "
        "choose highest validation R², then lower RMSE on validation; "
        "optional tie-break: lower CV R² std or smaller train–val gap."
    )

    rationale = (
        f"Selected **{best_name}** by **validation** R²={best_row['val_r2']:.4f} (minimize RMSE). "
        "Split: 70% train / 10% val / 20% test (patient groups; stratified by patient median dose). "
        f"Feature count N={best_n} chosen on validation probe. "
        "RandomizedSearchCV on train with GroupKFold. "
    )
    if rationale_extra:
        rationale += rationale_extra + " "
    rationale += (
        f"Test set: R²={best_row['test_r2']:.4f}, RMSE={best_row['test_rmse']:.4f}, MAE={best_row['test_mae']:.4f}. "
        f"Train–val R² gap={best_row['overfit_gap_r2_train_val']:.4f} "
        f"(CV R² std={cv_by_model.get(best_name, {}).get('cv_r2_std', float('nan')):.4f})."
    )

    if not skip_lstm:
        logger.info("LSTM benchmark is classification-oriented; skipped for regression pipeline.")

    y_tr_s = pd.to_numeric(train_df[config.COL_TARGET], errors="coerce")
    train_insulin_mean = float(y_tr_s.mean())
    train_insulin_std = float(y_tr_s.std()) if y_tr_s.std() == y_tr_s.std() else 1.0
    edges = pre.insulin_bin_edges
    edges_list = edges.tolist() if edges is not None else None

    numeric_defaults = {
        c: float(train_df[c].median())
        for c in config.NUMERIC_FEATURES
        if c in train_df.columns and pd.to_numeric(train_df[c], errors="coerce").notna().any()
    }
    bundle = ProductionBundle(
        model=best_model,
        model_name=best_name,
        preprocessor=pre,
        metadata={
            "task": "regression",
            "data_path": str(data_path),
            "n_train": len(train_df),
            "n_val": len(val_df),
            "n_test": len(test_df),
            "split": "70_train_10_val_20_test_stratified_groups",
            "selected_feature_count": int(best_n),
            "numeric_defaults": numeric_defaults,
            "insulin_bin_edges": edges_list,
            "train_insulin_mean": train_insulin_mean,
            "train_insulin_std": train_insulin_std,
            "r2_test": float(best_row["test_r2"]),
            "r2_val": float(best_row["val_r2"]),
            "r2_train": float(best_row["train_r2"]),
            "rmse_test": float(best_row["test_rmse"]),
            "rmse_val": float(best_row["val_rmse"]),
            "mae_test": float(best_row["test_mae"]),
            "mae_val": float(best_row["val_mae"]),
            "train_val_gap_r2": float(best_row["overfit_gap_r2_train_val"]),
            "tuning": {"n_iter": config.TUNING_N_ITER, "cv_folds": config.TUNING_CV_FOLDS},
            "cv_r2_std": cv_by_model.get(best_name, {}).get("cv_r2_std"),
            "eda_report_path": str(out_dir / "eda" / "eda_summary.json"),
            "evaluation_report_path": str((out_dir / "evaluation_report.json").resolve()),
            "best_model_for_deployment": best_name,
            "metrics_all_splits": best_model_metrics_nested(best_row_gs),
            "generalized_evaluation_score": float(best_row_gs["generalized_evaluation_score"]),
            "selection_rule": selection_rule,
        },
    )
    save_model(bundle, out_dir / "model_bundle")

    eval_report = build_evaluation_report(
        comp_enriched,
        best_name,
        selection_rule,
        out_dir,
        out_dir / "model_bundle",
        repo_root=repo_root,
    )
    write_evaluation_report(eval_report, out_dir / "evaluation_report.json")
    logger.info(
        "Evaluation report: %s | Set SMART_SENSOR_BUNDLE_DIR=%s to load this bundle in the API.",
        out_dir / "evaluation_report.json",
        (out_dir / "model_bundle").resolve(),
    )

    _bg_n = min(100, len(train_df))
    rng = np.random.RandomState(random_state)
    _idx = rng.choice(len(train_df), size=_bg_n, replace=False)
    X_shap_bg = pre.transform(train_df.iloc[_idx])
    np.save(out_dir / "model_bundle" / "shap_background.npy", X_shap_bg)
    logger.info("Saved SHAP background matrix %s for /api/explain", X_shap_bg.shape)

    example_row = test_df.iloc[0].to_dict()
    example_out = predict_new_data(bundle, example_row, with_recommendation=True)

    stages_doc = out_dir / "PIPELINE_STAGES.md"
    stages_doc.write_text(
        "\n".join(
            [
                "# Smart Sensor ML pipeline stages (regression)",
                "",
                "1. **load_data()** — CSV → DataFrame; EDA summary + `eda/eda_summary.json`.",
                "2. **validate_data()** — schema, duplicates, soft domain bounds.",
                "3. **PreprocessPipeline.fit/transform** — time features, derived ratios, patient encoding, IQR clip, median impute, MI (regression), correlation filter, StandardScaler.",
                "4. **Target** — `Insulin_Dose` continuous (units).",
                "5. **MI ranking + validation N** — probe feature counts on val; **RandomizedSearchCV** (GroupKFold on train) — Ridge, Lasso, ElasticNet, RF, GB, XGBoost (optional), LightGBM if SMART_SENSOR_TRY_LGBM=1.",
                "6. **Metrics** — R², RMSE, MAE on train/val/test; residual plots.",
                "7. **predict_new_data()** — predicted dose + dose→tier (train tertiles) for API.",
                "8. **recommend()** — rule-based care guidance by tier.",
                "9. **save_model** — `model_bundle/bundle.joblib` + metadata.",
                "",
                f"Best model: **{best_name}**. See `evaluation_report.json`, `model_comparison.csv`, and `Smart_Sensor_ML_Report.pdf`.",
            ]
        ),
        encoding="utf-8",
    )

    figs_for_pdf = sorted(fig_dir.glob("residuals_*.png"))[:2]
    figs_for_pdf += sorted(fig_dir.glob("importance_*.png"))[:1]
    figs_for_pdf += sorted(fig_dir.glob("pred_vs_actual_*.png"))[:1]
    figs_for_pdf += [fig_dir / "distributions_glucose_insulin.png"]

    build_pdf_report(
        out_dir / "Smart_Sensor_ML_Report.pdf",
        summary=eda,
        comparison_df=comp,
        best_model_name=best_name,
        selection_rationale=rationale,
        example_prediction=example_out,
        figure_paths=figs_for_pdf,
    )

    print("\n=== Done ===")
    print("Comparison:\n", comp.to_string(index=False))
    print("\nExample prediction:\n", json.dumps(example_out, indent=2, default=str)[:2000])
    print(f"\nArtifacts: {out_dir}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Smart Sensor Diabetes ML pipeline (insulin dose regression)")
    p.add_argument("--data", type=Path, default=None, help="Path to SmartSensor CSV")
    p.add_argument("--out", type=Path, default=None, help="Output directory")
    p.add_argument("--skip-lstm", action="store_true", help="(Default) LSTM benchmark skipped for regression")
    p.add_argument("--seed", type=int, default=config.RANDOM_STATE)
    args = p.parse_args(argv)
    data_path = args.data or config.default_data_path()
    out_dir = args.out or config.default_output_dir()
    if not data_path.is_file():
        logger.error("Data not found: %s", data_path)
        return 1
    run_pipeline(data_path, out_dir, skip_lstm=True, random_state=args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
