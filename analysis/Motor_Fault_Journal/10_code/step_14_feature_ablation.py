"""Step 14: frozen time/frequency/combined feature-family ablation."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
from sklearn.base import clone

from ml_metrics import PRIMARY_LABELS, classification_metrics
from step_12_primary_benchmark import candidates, load_inputs


PROJECT = Path(__file__).resolve().parents[1]
PRIMARY_DIR = PROJECT / "09_results" / "step_12_primary"
RESULT_DIR = PROJECT / "09_results" / "step_14_feature_ablation"
LOCK_FILE = RESULT_DIR / "TEST_EVALUATION_LOCK.json"


def main() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        raise RuntimeError("Step 14 ablation has already evaluated its supporting test models")
    LOCK_FILE.write_text(json.dumps({
        "status": "STARTED",
        "policy": "Reuse combined Step 12 predictions; evaluate one frozen time-only and one frozen frequency-only model."
    }, indent=2), encoding="utf-8")

    frame, feature_sets = load_inputs()
    leaderboard = pd.read_csv(PRIMARY_DIR / "validation_leaderboard.csv")
    primary_predictions = pd.read_csv(PRIMARY_DIR / "test_predictions.csv")
    development = frame[frame["split"].isin(["train", "validation"])]
    test = frame[frame["split"] == "test"].copy()
    rows = []

    for family in ["time_domain", "frequency_domain", "combined"]:
        selected = leaderboard[leaderboard["feature_family"] == family].iloc[0]
        if family == "combined":
            joined = test[["window_hash", "label"]].merge(
                primary_predictions[["window_hash", "prediction"]],
                on="window_hash", how="left", validate="one_to_one"
            )
            prediction = joined["prediction"]
            fit_seconds = float("nan")
            inference_seconds = float("nan")
            source = "reused protected Step 12 predictions"
        else:
            model = clone(candidates()[selected["classifier"]][int(selected["variant_index"])])
            columns = feature_sets[family]
            started = time.perf_counter()
            model.fit(development[columns], development["label"])
            fit_seconds = time.perf_counter() - started
            started = time.perf_counter()
            prediction = model.predict(test[columns])
            inference_seconds = time.perf_counter() - started
            source = "prespecified supporting ablation prediction"
            pd.DataFrame({
                "window_hash": test["window_hash"].to_numpy(),
                "label": test["label"].to_numpy(),
                "prediction": prediction,
            }).to_csv(RESULT_DIR / f"{family}_test_predictions.csv", index=False)

        metrics = classification_metrics(test["label"], prediction, PRIMARY_LABELS)
        rows.append({
            "feature_family": family,
            "classifier": selected["classifier"],
            "variant_index": int(selected["variant_index"]),
            "validation_macro_f1": selected["validation_macro_f1"],
            **metrics,
            "refit_seconds": fit_seconds,
            "inference_seconds": inference_seconds,
            "prediction_source": source,
        })

    result = pd.DataFrame(rows)
    combined_f1 = float(result.loc[result["feature_family"] == "combined", "macro_f1"].iloc[0])
    result["macro_f1_difference_from_combined"] = result["macro_f1"] - combined_f1
    result.to_csv(RESULT_DIR / "feature_family_ablation.csv", index=False)
    LOCK_FILE.write_text(json.dumps({
        "status": "COMPLETED",
        "combined_prediction_reused": True,
        "new_supporting_test_models": 2,
    }, indent=2), encoding="utf-8")
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
