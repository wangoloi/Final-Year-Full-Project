"""
Run Recommendation System (Step 6): load best model, run prediction, generate clinical
recommendations and natural language explanations.

Usage:
  python scripts/pipeline/run_recommendation.py
  python scripts/pipeline/run_recommendation.py --data data/SmartSensor_DiabetesMonitoring.csv --patients 5
  python scripts/pipeline/run_recommendation.py --model-dir outputs/best_model --input-csv path/to/patients.csv
"""
import argparse
import json
import logging
import sys
import warnings
from pathlib import Path

import numpy as np

# Suppress sklearn version mismatch warnings when loading older saved models
warnings.filterwarnings("ignore", message=".*Trying to unpickle.*", category=UserWarning)

from repo_paths import REPO_ROOT, SRC, DEFAULT_DATA_CSV

sys.path.insert(0, str(SRC))

from insulin_system.config.schema import DataSchema, PipelineConfig
from insulin_system.data_processing.load import DataLoader
from insulin_system.data_processing.pipeline import DataProcessingPipeline
from insulin_system.data_processing.split import TemporalSplitter
from insulin_system.persistence import load_best_model
from insulin_system.recommendation import (
    PredictionEngine,
    RecommendationGenerator,
    RecommendationExplanationGenerator,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Recommendation system: predict and explain")
    parser.add_argument("--model-dir", type=Path, default=REPO_ROOT / "outputs/best_model")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_CSV,
                        help="Dataset to use for reference (similar patients) and optional input")
    parser.add_argument("--input-csv", type=Path, default=None,
                        help="Optional CSV of patients to run (same schema); else use --patients from --data")
    parser.add_argument("--patients", type=int, nargs="?", default=5, const=5,
                        metavar="N",
                        help="Number of patients from test set to run when using --data (default: 5)")
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/recommendations"))
    parser.add_argument("--no-eda", action="store_true")
    parser.add_argument("--no-feature-selection", action="store_true")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    if not args.model_dir.joinpath("inference_bundle.joblib").exists():
        logger.error("No saved model at %s. Run: python scripts/pipeline/run_evaluation.py [--best-model-dir %s]", args.model_dir, args.model_dir)
        return 1

    bundle = load_best_model(args.model_dir)
    engine = PredictionEngine(bundle=bundle)
    rec_gen = RecommendationGenerator()
    feature_names = bundle.feature_names
    classes = bundle.classes_

    reference_X = None
    reference_y = None
    input_df = None
    use_ref_for_similar = False

    if args.input_csv and args.input_csv.exists():
        import pandas as pd
        input_df = pd.read_csv(args.input_csv)
        logger.info("Loaded %d rows from %s", len(input_df), args.input_csv)
    elif args.data.exists():
        schema = DataSchema()
        pipeline_config = PipelineConfig()
        # Load raw data and apply same temporal split to get raw test rows (bundle expects raw columns)
        loader = DataLoader(schema=schema, file_path=args.data)
        raw_df = loader.load_and_validate(args.data)
        splitter = TemporalSplitter(
            schema=schema,
            train_ratio=pipeline_config.train_ratio,
            val_ratio=pipeline_config.val_ratio,
            random_state=pipeline_config.random_state,
        )
        _train_df, _val_df, raw_test_df = splitter.split(raw_df, sort_by=schema.PATIENT_ID)
        n = min(args.patients, len(raw_test_df))
        input_df = raw_test_df.head(n).drop(columns=[schema.TARGET], errors="ignore").copy()

        # Run full pipeline to get reference set for similar-patient lookup (uses encoded X_test)
        pipeline = DataProcessingPipeline(data_path=args.data)
        pipeline_result = pipeline.run(
            data_path=args.data,
            run_eda=not args.no_eda,
            run_feature_selection=not args.no_feature_selection,
        )
        reference_X = pipeline_result.X_test.values
        reference_y = pipeline_result.y_test.values
        use_ref_for_similar = True
        logger.info("Using %d test patients from pipeline; reference set size %d", n, len(reference_X))
    else:
        logger.error("Provide --data or --input-csv with existing file")
        return 1

    if input_df is None or len(input_df) == 0:
        logger.error("No input patients to run")
        return 1

    X_trans = engine.bundle.transform(input_df)
    expl_gen = RecommendationExplanationGenerator(
        reference_X=reference_X,
        reference_y=reference_y,
        feature_names=feature_names,
    )

    results = []
    for i in range(len(input_df)):
        proba = engine.bundle.predict_proba(X_trans[i : i + 1])[0]
        label = engine.bundle.predict(X_trans[i : i + 1])[0]
        conf = float(proba[list(classes).index(label)])
        eps = 1e-10
        ent = float(-(proba * np.log(proba + eps)).sum())
        prob_breakdown = {str(c): float(proba[j]) for j, c in enumerate(classes)}
        rec = rec_gen.generate(str(label), conf, ent, prob_breakdown)
        query_idx = i if (use_ref_for_similar and reference_X is not None and i < len(reference_X)) else None
        expl = expl_gen.generate(
            rec,
            patient_features=X_trans[i],
            predicted_class=str(label),
            proba=proba,
            query_index_in_ref=query_idx,
        )
        results.append({
            "patient_index": i,
            "predicted_class": rec.predicted_class,
            "confidence": rec.confidence,
            "is_high_risk": rec.is_high_risk,
            "recommendation_summary": rec.dosage_suggestion.summary,
            "natural_language": expl.natural_language_summary,
            "alternative_scenarios": expl.alternative_scenarios,
            "similar_patients_summary": expl.similar_patients_summary,
        })

    out_json = args.out_dir / "recommendations.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    logger.info("Wrote %s", out_json)

    out_md = args.out_dir / "recommendations_summary.md"
    lines = ["# Recommendation System Output", ""]
    for r in results:
        lines.append(f"## Patient {r['patient_index']}")
        lines.append(r["natural_language"])
        lines.append("")
        lines.append("### Alternative scenarios")
        for s in r["alternative_scenarios"]:
            lines.append(f"- {s}")
        if r.get("similar_patients_summary"):
            lines.append(f"\n{r['similar_patients_summary']}")
        lines.append("")
    out_md.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Wrote %s", out_md)

    return 0


if __name__ == "__main__":
    sys.exit(main())
