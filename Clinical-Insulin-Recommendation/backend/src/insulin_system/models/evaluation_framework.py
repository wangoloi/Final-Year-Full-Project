"""
Comprehensive Model Evaluation Framework (Step 4).
- Classification metrics (accuracy, precision/recall/F1 macro+weighted)
- Confusion matrix visualization
- ROC-AUC One-vs-Rest, calibration curves, learning curves
- Feature importance (built-in + permutation), temporal validation
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.inspection import permutation_importance
from sklearn.metrics import auc, roc_curve
from sklearn.model_selection import StratifiedKFold, learning_curve

from ..config.schema import EvaluationConfig, ModelConfig
from ..data_processing.pipeline import PipelineResult
from .evaluation import EvaluationResult, evaluate_model

logger = logging.getLogger(__name__)


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _class_order(estimator: Any, y: np.ndarray) -> np.ndarray:
    classes_ = getattr(estimator, "classes_", None)
    if classes_ is None and hasattr(estimator, "named_steps"):
        classes_ = getattr(estimator.named_steps.get("clf"), "classes_", None)
    return np.array(classes_) if classes_ is not None else np.unique(y)


def _label_to_index_map(classes: np.ndarray) -> Dict[Any, int]:
    return {c: i for i, c in enumerate(classes)}


def _binarize_y(y: np.ndarray, classes: np.ndarray) -> np.ndarray:
    m = _label_to_index_map(classes)
    y_idx = np.array([m.get(v, 0) for v in y], dtype=int)
    out = np.zeros((len(y_idx), len(classes)), dtype=int)
    out[np.arange(len(y_idx)), y_idx] = 1
    return out


def _safe_predict_proba(estimator: Any, X: np.ndarray) -> Optional[np.ndarray]:
    if hasattr(estimator, "predict_proba"):
        try:
            return estimator.predict_proba(X)
        except Exception:
            return None
    return None


@dataclass
class FullEvaluationArtifacts:
    model_name: str
    metrics_test: EvaluationResult
    metrics_train: Optional[EvaluationResult] = None
    metrics_val: Optional[EvaluationResult] = None
    temporal_metrics: Optional[pd.DataFrame] = None
    paths: Dict[str, str] = field(default_factory=dict)


class EvaluationFramework:
    """Runs comprehensive evaluation and writes artifacts to disk."""

    def __init__(
        self,
        eval_config: Optional[EvaluationConfig] = None,
        model_config: Optional[ModelConfig] = None,
    ) -> None:
        self._cfg = eval_config or EvaluationConfig()
        self._m_cfg = model_config or ModelConfig()

    def run_for_model(
        self,
        model_name: str,
        estimator: Any,
        pipeline_result: PipelineResult,
        output_dir: Optional[Path] = None,
    ) -> FullEvaluationArtifacts:
        out_dir = _ensure_dir(Path(output_dir) if output_dir else self._cfg.ensure_output_dir())
        model_dir = _ensure_dir(out_dir / model_name)

        X_train = pipeline_result.X_train.values
        y_train = pipeline_result.y_train.values
        X_val = pipeline_result.X_val.values if len(pipeline_result.X_val) > 0 else np.array([])
        y_val = pipeline_result.y_val.values if len(pipeline_result.y_val) > 0 else np.array([])
        X_test = pipeline_result.X_test.values
        y_test = pipeline_result.y_test.values

        labels = list(np.unique(y_test))
        ev_test = evaluate_model(estimator, X_test, y_test, model_name=model_name, labels=labels)
        ev_train = evaluate_model(estimator, X_train, y_train, model_name=model_name, labels=labels)
        ev_val = evaluate_model(estimator, X_val, y_val, model_name=model_name, labels=labels) if len(X_val) > 0 else None

        paths: Dict[str, str] = {}
        def _to_serializable(d: dict) -> dict:
            out = {}
            for k, v in d.items():
                if hasattr(v, "tolist"):
                    out[k] = v.tolist()
                elif isinstance(v, (np.floating, np.integer)):
                    out[k] = float(v)
                else:
                    out[k] = v
            return out
        from sklearn.metrics import precision_recall_fscore_support
        y_pred_test = estimator.predict(X_test)
        p_per, r_per, f_per, _ = precision_recall_fscore_support(
            y_test, y_pred_test, labels=labels, zero_division=0
        )
        per_class = [
            {"class": labels[i], "precision": float(p_per[i]), "recall": float(r_per[i]), "f1": float(f_per[i])}
            for i in range(len(labels))
        ]
        ev_test_dict = _to_serializable(ev_test.__dict__)
        if hasattr(ev_test, "classification_report_str") and ev_test.classification_report_str:
            ev_test_dict["classification_report"] = ev_test.classification_report_str
        payload = {
            "test": ev_test_dict,
            "train": _to_serializable(ev_train.__dict__),
            "val": _to_serializable(ev_val.__dict__) if ev_val is not None else {},
            "per_class_metrics": per_class,
        }
        metrics_path = model_dir / "metrics.json"
        metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        paths["metrics_json"] = str(metrics_path)

        if self._cfg.plot_confusion_matrix:
            p = self._plot_confusion_matrix(ev_test.confusion_matrix, labels, model_dir / "confusion_matrix.png")
            paths["confusion_matrix"] = str(p)

        proba = _safe_predict_proba(estimator, X_test)
        classes = _class_order(estimator, y_test)

        if self._cfg.plot_roc_auc_ovr and proba is not None:
            p = self._plot_roc_ovr(y_test, proba, classes, model_dir / "roc_ovr.png")
            paths["roc_ovr"] = str(p)

        if self._cfg.plot_calibration and proba is not None:
            p = self._plot_calibration(y_test, proba, classes, model_dir / "calibration.png")
            paths["calibration"] = str(p)

        if self._cfg.plot_learning_curve and model_name != "rnn_lstm":
            # RNN/LSTM does not support sklearn clone (stateful); skip learning curve
            p = self._plot_learning_curve(
                estimator, X_train, y_train,
                model_dir / "learning_curve.png",
                train_sizes=self._cfg.learning_curve_train_sizes,
            )
            if p is not None:
                paths["learning_curve"] = str(p)

        if self._cfg.plot_feature_importance:
            p1 = self._plot_builtin_feature_importance(
                estimator, pipeline_result.feature_names, model_dir / "feature_importance_builtin.png"
            )
            if p1:
                paths["feature_importance_builtin"] = str(p1)
            p2 = self._plot_permutation_importance(
                estimator, pipeline_result.X_test, pipeline_result.y_test,
                model_dir / "feature_importance_permutation.png",
            )
            if p2:
                paths["feature_importance_permutation"] = str(p2)

        temporal_df = self._temporal_validation(estimator, pipeline_result, labels)
        if temporal_df is not None:
            csv_path = model_dir / "temporal_validation.csv"
            temporal_df.to_csv(csv_path, index=False)
            paths["temporal_validation_csv"] = str(csv_path)

        return FullEvaluationArtifacts(
            model_name=model_name,
            metrics_test=ev_test,
            metrics_train=ev_train,
            metrics_val=ev_val,
            temporal_metrics=temporal_df,
            paths=paths,
        )

    def run_for_many(
        self,
        models: Sequence[Tuple[str, Any]],
        pipeline_result: PipelineResult,
        output_dir: Optional[Path] = None,
    ) -> pd.DataFrame:
        rows = []
        out_dir = Path(output_dir) if output_dir else self._cfg.ensure_output_dir()
        for name, est in models:
            logger.info("Evaluating model: %s", name)
            art = self.run_for_model(name, est, pipeline_result, output_dir=out_dir)
            rows.append({
                "model": name,
                "accuracy": art.metrics_test.accuracy,
                "f1_weighted": art.metrics_test.f1_weighted,
                "f1_macro": art.metrics_test.f1_macro,
                "roc_auc_weighted": art.metrics_test.roc_auc_ovr_weighted,
                "artifacts_dir": str(Path(out_dir) / name),
            })
        df = pd.DataFrame(rows).sort_values("f1_weighted", ascending=False)
        df.to_csv(Path(out_dir) / "evaluation_summary.csv", index=False)
        # Plot model comparison
        self._plot_model_comparison(df, out_dir)
        return df

    def _plot_model_comparison(self, summary_df: pd.DataFrame, out_dir: Path) -> "Optional[Path]":
        """Plot model comparison bar chart."""
        try:
            fig, ax = plt.subplots(figsize=(10, 5))
            metrics = ["f1_weighted", "accuracy", "roc_auc_weighted"]
            df_plot = summary_df.set_index("model")[[c for c in metrics if c in summary_df.columns]]
            if df_plot.empty:
                return None
            df_plot.plot(kind="bar", ax=ax, width=0.8)
            ax.set_title("Model Comparison", fontsize=14, fontweight="bold")
            ax.set_xlabel("Model")
            ax.set_ylabel("Score")
            ax.legend(title="Metric")
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
            ax.grid(True, alpha=0.3, axis="y")
            plt.tight_layout()
            p = Path(out_dir) / "model_comparison.png"
            plt.savefig(p, dpi=150, bbox_inches="tight")
            plt.close()
            return p
        except Exception as e:
            logger.warning("Model comparison plot failed: %s", e)
            return None

    def _plot_confusion_matrix(self, cm: np.ndarray, labels: List[str], out_path: Path) -> Path:
        fig, ax = plt.subplots(figsize=(7, 6))
        df_cm = pd.DataFrame(cm, index=labels, columns=labels)
        sns.heatmap(df_cm, annot=True, fmt="d", cmap="Blues", ax=ax, cbar_kws={"label": "Count"})
        ax.set_title("Confusion Matrix (Test)", fontsize=14, fontweight="bold")
        ax.set_ylabel("True Label")
        ax.set_xlabel("Predicted Label")
        plt.tight_layout()
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()
        return out_path

    def _plot_roc_ovr(self, y_true: np.ndarray, y_proba: np.ndarray, classes: np.ndarray, out_path: Path) -> Path:
        y_bin = _binarize_y(y_true, classes)
        fig, ax = plt.subplots(figsize=(8, 6))
        for i, c in enumerate(classes):
            fpr, tpr, _ = roc_curve(y_bin[:, i], y_proba[:, i])
            ax.plot(fpr, tpr, label=f"{c} (AUC={auc(fpr, tpr):.3f})", linewidth=2)
        ax.plot([0, 1], [0, 1], "k--", linewidth=1, alpha=0.5)
        ax.set_title("ROC Curves (One-vs-Rest)", fontsize=14, fontweight="bold")
        ax.set_xlabel("False Positive Rate")
        ax.set_ylabel("True Positive Rate")
        ax.legend(fontsize=9, loc="lower right", frameon=True)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()
        return out_path

    def _plot_calibration(self, y_true: np.ndarray, y_proba: np.ndarray, classes: np.ndarray, out_path: Path) -> Path:
        from sklearn.calibration import calibration_curve
        y_bin = _binarize_y(y_true, classes)
        plt.figure(figsize=(7, 6))
        for i, c in enumerate(classes):
            prob_true, prob_pred = calibration_curve(y_bin[:, i], y_proba[:, i], n_bins=10, strategy="uniform")
            plt.plot(prob_pred, prob_true, marker="o", linewidth=1, label=str(c))
        plt.plot([0, 1], [0, 1], "k--", linewidth=1)
        plt.title("Calibration Curves (Per Class)")
        plt.xlabel("Mean Predicted Probability")
        plt.ylabel("Fraction of Positives")
        plt.legend(fontsize=8, loc="upper left")
        plt.tight_layout()
        plt.savefig(out_path, dpi=120)
        plt.close()
        return out_path

    def _plot_learning_curve(
        self,
        estimator: Any,
        X: np.ndarray,
        y: np.ndarray,
        out_path: Path,
        train_sizes: Tuple[float, ...],
    ) -> Optional[Path]:
        """Plot learning curve. Uses n_jobs=1 to avoid Windows parallel CV returning empty results."""
        try:
            cv = StratifiedKFold(n_splits=self._m_cfg.cv_folds, shuffle=True, random_state=self._m_cfg.random_state)
            sizes, train_scores, val_scores = learning_curve(
                estimator, X, y,
                train_sizes=np.array(train_sizes),
                cv=cv,
                scoring=self._m_cfg.scoring,
                n_jobs=1,
            )
            if train_scores.size == 0 or val_scores.size == 0:
                logger.warning("Learning curve returned empty scores; skipping plot")
                return None
            train_mean, train_std = train_scores.mean(axis=1), train_scores.std(axis=1)
            val_mean, val_std = val_scores.mean(axis=1), val_scores.std(axis=1)
            plt.figure(figsize=(7, 5))
            plt.plot(sizes, train_mean, "o-", label="Train")
            plt.plot(sizes, val_mean, "o-", label="CV")
            plt.fill_between(sizes, train_mean - train_std, train_mean + train_std, alpha=0.15)
            plt.fill_between(sizes, val_mean - val_std, val_mean + val_std, alpha=0.15)
            plt.title("Learning Curve")
            plt.xlabel("Training Examples")
            plt.ylabel(self._m_cfg.scoring)
            plt.legend()
            plt.tight_layout()
            plt.savefig(out_path, dpi=120)
            plt.close()
            return out_path
        except Exception as e:
            logger.warning("Learning curve failed (%s); skipping plot", e)
            return None

    def _plot_builtin_feature_importance(
        self,
        estimator: Any,
        feature_names: List[str],
        out_path: Path,
        top_k: int = 20,
    ) -> Optional[Path]:
        est = estimator
        if hasattr(estimator, "named_steps") and "clf" in getattr(estimator, "named_steps", {}):
            est = estimator.named_steps["clf"]
        importance = None
        if hasattr(est, "feature_importances_"):
            importance = np.asarray(est.feature_importances_)
        elif hasattr(est, "coef_"):
            coef = np.asarray(est.coef_)
            importance = np.mean(np.abs(coef), axis=0)
        if importance is None or len(importance) != len(feature_names):
            return None
        idx = np.argsort(importance)[::-1][:top_k]
        plt.figure(figsize=(8, 5))
        sns.barplot(x=importance[idx].tolist(), y=np.array(feature_names)[idx].tolist())
        plt.title("Built-in Feature Importance (Top)")
        plt.tight_layout()
        plt.savefig(out_path, dpi=120)
        plt.close()
        return out_path

    def _plot_permutation_importance(
        self,
        estimator: Any,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        out_path: Path,
        top_k: int = 20,
    ) -> Optional[Path]:
        try:
            r = permutation_importance(
                estimator,
                X_test.values,
                y_test.values,
                scoring=self._m_cfg.scoring,
                n_repeats=self._cfg.permutation_repeats,
                random_state=self._m_cfg.random_state,
                n_jobs=self._m_cfg.n_jobs,
            )
        except Exception:
            return None
        imp = r.importances_mean
        names = np.array(list(X_test.columns))
        idx = np.argsort(imp)[::-1][:top_k]
        plt.figure(figsize=(8, 5))
        sns.barplot(x=imp[idx].tolist(), y=names[idx].tolist())
        plt.title("Permutation Importance (Top)")
        plt.tight_layout()
        plt.savefig(out_path, dpi=120)
        plt.close()
        return out_path

    def _temporal_validation(
        self,
        estimator: Any,
        pipeline_result: PipelineResult,
        labels: List[str],
    ) -> Optional[pd.DataFrame]:
        seg_col = self._cfg.temporal_segment_column
        if seg_col not in pipeline_result.test.columns:
            return None
        df = pipeline_result.test[[seg_col]].copy()
        df["y_true"] = pipeline_result.y_test.values
        rows = []
        for seg in sorted(df[seg_col].unique().tolist()):
            idx = df.index[df[seg_col] == seg]
            if len(idx) < 10:
                continue
            X_seg = pipeline_result.X_test.loc[idx].values
            y_seg = pipeline_result.y_test.loc[idx].values
            ev = evaluate_model(estimator, X_seg, y_seg, model_name="tmp", labels=labels)
            rows.append({
                "temporal_segment": seg,
                "n": len(idx),
                "accuracy": ev.accuracy,
                "f1_weighted": ev.f1_weighted,
                "f1_macro": ev.f1_macro,
            })
        return pd.DataFrame(rows) if rows else None

