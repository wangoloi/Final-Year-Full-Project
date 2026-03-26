"""
Exploratory Data Analysis (EDA) module.
Produces summary statistics and visualizations for the insulin dosage dataset.
"""

import logging
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from ..config.schema import DataSchema, EDAPathConfig
from ..exceptions import DataValidationError

logger = logging.getLogger(__name__)
EDA_STYLE = {"figure.figsize": (10, 6), "axes.titlesize": 12}


class EDAAnalyzer:
    """Performs EDA and writes artifacts to disk."""

    def __init__(
        self,
        schema: Optional[DataSchema] = None,
        path_config: Optional[EDAPathConfig] = None,
    ) -> None:
        self._schema = schema or DataSchema()
        self._paths = path_config or EDAPathConfig()

    def _ensure_output_dir(self) -> Path:
        return self._paths.ensure_output_dir()

    def run(
        self,
        df: pd.DataFrame,
        output_dir: Optional[Path] = None,
        summary_stream: Optional[object] = None,
    ) -> str:
        """Run full EDA: summary stats and all visualizations."""
        out = Path(output_dir) if output_dir else self._ensure_output_dir()
        out.mkdir(parents=True, exist_ok=True)
        summary_lines = []
        summary_lines.append("=== EDA Summary ===\n")
        summary_lines.append("Shape: {} rows, {} columns\n".format(df.shape[0], df.shape[1]))
        summary_lines.append("Missing counts:\n" + df.isnull().sum().to_string() + "\n")
        summary_lines.append("Target:\n" + df[self._schema.TARGET].value_counts().to_string() + "\n")
        numeric_cols = [c for c in self._schema.NUMERIC if c in df.columns]
        if numeric_cols:
            summary_lines.append("\nNumeric summary:\n")
            summary_lines.append(df[numeric_cols].describe().to_string())
            summary_lines.append("\n")
        summary_text = "".join(summary_lines)
        if summary_stream is not None and hasattr(summary_stream, "write"):
            summary_stream.write(summary_text)
        summary_path = out / self._paths.summary_file
        summary_path.write_text(summary_text, encoding="utf-8")
        logger.info("EDA summary written to %s", summary_path)
        self._plot_missing(df, out)
        self._plot_target(df, out)
        self._plot_distributions(df, out)
        self._plot_correlation(df, out)
        self._plot_outliers_boxplot(df, out)
        return str(out)

    def _plot_missing(self, df: pd.DataFrame, out: Path) -> None:
        missing = df.isnull().sum()
        if missing.sum() == 0:
            missing = missing[missing.index.isin(self._schema.all_columns)]
        else:
            missing = missing[missing > 0].sort_values(ascending=False)
        if missing.empty:
            missing = df[self._schema.feature_columns].isnull().sum()
        with plt.style.context(EDA_STYLE):
            fig, ax = plt.subplots()
            missing.plot(kind="bar", ax=ax, color="steelblue", edgecolor="navy")
            ax.set_title("Missing Values per Column")
            ax.set_ylabel("Count")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            fig.savefig(out / self._paths.missing_plot, dpi=100, bbox_inches="tight")
            plt.close(fig)

    def _plot_target(self, df: pd.DataFrame, out: Path) -> None:
        if self._schema.TARGET not in df.columns:
            raise DataValidationError("Target column not in DataFrame.")
        with plt.style.context(EDA_STYLE):
            fig, ax = plt.subplots()
            df[self._schema.TARGET].value_counts().sort_index().plot(
                kind="bar", ax=ax, color=["#2ecc71", "#3498db", "#e74c3c", "#95a5a6"]
            )
            ax.set_title("Insulin Dosage Category (Target) Distribution")
            ax.set_ylabel("Count")
            ax.set_xlabel("Category")
            plt.xticks(rotation=0)
            plt.tight_layout()
            fig.savefig(out / self._paths.target_plot, dpi=100, bbox_inches="tight")
            plt.close(fig)

    def _plot_distributions(self, df: pd.DataFrame, out: Path) -> None:
        numeric = [c for c in self._schema.NUMERIC if c in df.columns]
        if not numeric:
            return
        n_cols = 3
        n_rows = (len(numeric) + n_cols - 1) // n_cols
        with plt.style.context(EDA_STYLE):
            fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 3 * n_rows))
            axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]
            for idx, col in enumerate(numeric):
                ax = axes_flat[idx] if idx < len(axes_flat) else axes_flat[-1]
                df[col].dropna().hist(ax=ax, bins=30, color="steelblue", edgecolor="white")
                ax.set_title(col)
                ax.set_ylabel("Count")
            for idx in range(len(numeric), len(axes_flat)):
                axes_flat[idx].set_visible(False)
            plt.tight_layout()
            fig.savefig(out / self._paths.distributions_plot, dpi=100, bbox_inches="tight")
            plt.close(fig)

    def _plot_correlation(self, df: pd.DataFrame, out: Path) -> None:
        numeric = [c for c in self._schema.NUMERIC if c in df.columns]
        if len(numeric) < 2:
            return
        with plt.style.context(EDA_STYLE):
            fig, ax = plt.subplots(figsize=(10, 8))
            corr = df[numeric].corr()
            sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax, square=True)
            ax.set_title("Correlation Matrix (Numeric Features)")
            plt.tight_layout()
            fig.savefig(out / self._paths.correlation_plot, dpi=100, bbox_inches="tight")
            plt.close(fig)

    def _plot_outliers_boxplot(self, df: pd.DataFrame, out: Path) -> None:
        numeric = [c for c in self._schema.NUMERIC if c in df.columns]
        if not numeric:
            return
        n_cols = 3
        n_rows = (len(numeric) + n_cols - 1) // n_cols
        with plt.style.context(EDA_STYLE):
            fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 3 * n_rows))
            axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]
            for idx, col in enumerate(numeric):
                ax = axes_flat[idx] if idx < len(axes_flat) else axes_flat[-1]
                df.boxplot(column=col, ax=ax)
                ax.set_title(col)
            for idx in range(len(numeric), len(axes_flat)):
                axes_flat[idx].set_visible(False)
            plt.tight_layout()
            fig.savefig(out / self._paths.outliers_plot, dpi=100, bbox_inches="tight")
            plt.close(fig)