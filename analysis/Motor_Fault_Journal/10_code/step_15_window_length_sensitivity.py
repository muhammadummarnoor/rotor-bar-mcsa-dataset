"""Step 15: 325/650/1300-sample window-length sensitivity analysis."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone

from ml_metrics import PRIMARY_LABELS, classification_metrics
from step_12_primary_benchmark import candidates, selection_phase
from train_benchmark import extract_current_runs, features_for_window, make_guarded_blocks


PROJECT = Path(__file__).resolve().parents[1]
FEATURE_DIR = PROJECT / "07_features" / "window_sensitivity"
RESULT_DIR = PROJECT / "09_results" / "step_15_window_sensitivity"
PRIMARY_FEATURES = PROJECT / "07_features" / "current_window_features.csv"
PRIMARY_RESULTS = PROJECT / "09_results" / "step_12_primary"
LOCK_FILE = RESULT_DIR / "TEST_EVALUATION_LOCK.json"
WINDOW_LENGTHS = [325, 650, 1300]


def feature_sets() -> dict[str, list[str]]:
    config = json.loads(
        (PROJECT / "05_data_manifest" / "frozen_feature_sets.json").read_text(encoding="utf-8")
    )
    return {
        "time_domain": config["time_domain"],
        "frequency_domain": config["frequency_domain"],
        "combined": config["time_domain"] + config["frequency_domain"],
    }


def build_features(length: int, by_class: dict, split_map: dict) -> pd.DataFrame:
    rows = []
    for label in PRIMARY_LABELS:
        for block in by_class[label]:
            values = block["values"]
            for start in range(0, len(values) - length + 1, length):
                window = values[start:start + length]
                row = features_for_window(window)
                row.update({
                    "label": label,
                    "split": split_map[block["block_id"]],
                    "run_id": block["run_id"],
                    "block_id": block["block_id"],
                    "window_start": start,
                    "window_samples": length,
                    "window_hash": hashlib.sha256(window.tobytes()).hexdigest(),
                })
                rows.append(row)
    frame = pd.DataFrame(rows)
    if frame.groupby("block_id")["split"].nunique().max() != 1:
        raise RuntimeError("A guarded block appears in multiple splits")
    if frame.groupby("window_hash")["split"].nunique().max() != 1:
        raise RuntimeError("A sensitivity window hash appears in multiple splits")
    return frame


def verify_650_reproduction(regenerated: pd.DataFrame, columns: list[str]) -> dict:
    frozen = pd.read_csv(PRIMARY_FEATURES)
    frozen = frozen[frozen["label"].isin(PRIMARY_LABELS)].copy()
    keys = ["label", "split", "run_id", "block_id", "window_start", "window_hash"]
    a = regenerated.sort_values(keys).reset_index(drop=True)
    b = frozen.sort_values(keys).reset_index(drop=True)
    checks = {
        "row_count_matches": len(a) == len(b),
        "identifiers_match": a[keys].equals(b[keys]),
        "feature_values_match": bool(np.allclose(
            a[columns].to_numpy(), b[columns].to_numpy(),
            rtol=1e-12, atol=1e-12, equal_nan=False,
        )),
    }
    checks["all_checks_pass"] = all(checks.values())
    return checks


def main() -> None:
    FEATURE_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        raise RuntimeError("Step 15 supporting test evaluation already exists; refusing rerun")
    LOCK_FILE.write_text(json.dumps({
        "status": "STARTED",
        "window_lengths": WINDOW_LENGTHS,
        "new_test_models": [325, 1300],
        "reused_primary_prediction_length": 650,
    }, indent=2), encoding="utf-8")

    runs = extract_current_runs()
    by_class, split_map = make_guarded_blocks(runs)
    families = feature_sets()
    all_columns = families["combined"]
    summary = []
    reproduction = None

    for length in WINDOW_LENGTHS:
        frame = build_features(length, by_class, split_map)
        frame.to_csv(FEATURE_DIR / f"features_{length}.csv", index=False)
        leaderboard, selected = selection_phase(frame, families)
        leaderboard.to_csv(RESULT_DIR / f"validation_leaderboard_{length}.csv", index=False)
        (RESULT_DIR / f"selected_configuration_{length}.json").write_text(
            json.dumps(selected, indent=2), encoding="utf-8"
        )

        test = frame[frame["split"] == "test"].copy()
        if length == 650:
            reproduction = verify_650_reproduction(frame, all_columns)
            if not reproduction["all_checks_pass"]:
                raise RuntimeError("Regenerated 650-sample table does not reproduce the frozen primary table")
            primary = pd.read_csv(PRIMARY_RESULTS / "test_predictions.csv")
            joined = test[["window_hash", "label"]].merge(
                primary[["window_hash", "prediction"]], on="window_hash", how="left", validate="one_to_one"
            )
            prediction = joined["prediction"]
            source = "reused Step 12 protected predictions"
            fit_seconds = float("nan")
            inference_seconds = float("nan")
        else:
            columns = families[selected["feature_family"]]
            development = frame[frame["split"].isin(["train", "validation"])]
            model = clone(candidates()[selected["classifier"]][selected["variant_index"]])
            started = time.perf_counter()
            model.fit(development[columns], development["label"])
            fit_seconds = time.perf_counter() - started
            started = time.perf_counter()
            prediction = model.predict(test[columns])
            inference_seconds = time.perf_counter() - started
            source = "prespecified sensitivity test prediction"
            pd.DataFrame({
                "window_hash": test["window_hash"].to_numpy(),
                "block_id": test["block_id"].to_numpy(),
                "label": test["label"].to_numpy(),
                "prediction": prediction,
            }).to_csv(RESULT_DIR / f"test_predictions_{length}.csv", index=False)

        metrics = classification_metrics(test["label"], prediction, PRIMARY_LABELS)
        summary.append({
            "window_samples": length,
            "window_seconds": length / 650.0,
            "frequency_resolution_hz": 650.0 / length,
            "windows_total": len(frame),
            "test_windows": len(test),
            "test_blocks": int(test["block_id"].nunique()),
            "selected_feature_family": selected["feature_family"],
            "selected_classifier": selected["classifier"],
            "selected_variant_index": selected["variant_index"],
            "validation_macro_f1": selected["validation_macro_f1"],
            **metrics,
            "refit_seconds": fit_seconds,
            "inference_seconds": inference_seconds,
            "prediction_source": source,
        })

    result = pd.DataFrame(summary)
    primary_f1 = float(result.loc[result["window_samples"] == 650, "macro_f1"].iloc[0])
    result["macro_f1_difference_from_650"] = result["macro_f1"] - primary_f1
    result.to_csv(RESULT_DIR / "window_length_sensitivity.csv", index=False)
    (RESULT_DIR / "reproduction_audit_650.json").write_text(
        json.dumps(reproduction, indent=2), encoding="utf-8"
    )
    LOCK_FILE.write_text(json.dumps({
        "status": "COMPLETED",
        "reproduction_650": reproduction,
        "new_supporting_test_models": 2,
    }, indent=2), encoding="utf-8")
    print(json.dumps(reproduction, indent=2))
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
