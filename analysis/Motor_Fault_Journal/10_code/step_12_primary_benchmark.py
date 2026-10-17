"""Step 12: primary F1/F2/F3 guard-separated time-blocked benchmark.

Default execution performs training/validation selection only.  Add
``--confirm-test`` once, after inspecting the saved validation leaderboard, to
refit the frozen winner and evaluate the protected test partition.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone

from ml_metrics import (
    BOOTSTRAP_RESAMPLES,
    PRIMARY_LABELS,
    classification_metrics,
    confusion_matrix_frame,
    per_class_metrics,
    stratified_block_bootstrap,
)
from train_benchmark import RANDOM_STATE, candidates


PROJECT = Path(__file__).resolve().parents[1]
FEATURE_FILE = PROJECT / "07_features" / "current_window_features.csv"
FEATURE_CONFIG = PROJECT / "05_data_manifest" / "frozen_feature_sets.json"
MODEL_CONFIG = PROJECT / "05_data_manifest" / "frozen_classifier_search.json"
SPLIT_AUDIT = PROJECT / "05_data_manifest" / "blocked_split_leakage_audit.json"
RESULT_DIR = PROJECT / "09_results" / "step_12_primary"
MODEL_DIR = PROJECT / "08_models"
LOCK_FILE = RESULT_DIR / "TEST_EVALUATION_LOCK.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def jsonable_params(model) -> dict[str, str | int | float | bool | None]:
    values = {}
    for key, value in model.named_steps["model"].get_params(deep=False).items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            values[key] = value
        else:
            values[key] = repr(value)
    return values


def load_inputs() -> tuple[pd.DataFrame, dict[str, list[str]]]:
    split_audit = json.loads(SPLIT_AUDIT.read_text(encoding="utf-8"))
    split_pass = split_audit.get("status") == "PASS" or split_audit.get("all_checks_pass") is True
    if not split_pass:
        raise RuntimeError("Blocked split audit is not PASS; refusing model training")

    config = json.loads(FEATURE_CONFIG.read_text(encoding="utf-8"))
    feature_sets = {
        "time_domain": config["time_domain"],
        "frequency_domain": config["frequency_domain"],
        "combined": config["time_domain"] + config["frequency_domain"],
    }
    frame = pd.read_csv(FEATURE_FILE)
    frame = frame[frame["label"].isin(PRIMARY_LABELS)].copy()
    required = set(sum(feature_sets.values(), [])) | {
        "label", "split", "block_id", "run_id", "window_hash", "window_start"
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Feature table is missing columns: {sorted(missing)}")
    if frame[list(required)].isna().any().any():
        raise ValueError("Primary feature table contains missing required values")
    if set(frame["split"]) != {"train", "validation", "test"}:
        raise ValueError("Expected train, validation and test partitions")
    if set(frame["label"]) != set(PRIMARY_LABELS):
        raise ValueError("Primary task does not contain all three drilled-fault classes")
    return frame, feature_sets


def selection_phase(
    frame: pd.DataFrame,
    feature_sets: dict[str, list[str]],
    labels: list[str] = PRIMARY_LABELS,
) -> tuple[pd.DataFrame, dict]:
    train = frame[frame["split"] == "train"]
    validation = frame[frame["split"] == "validation"]
    rows = []
    model_families = candidates()
    expected = 0
    for feature_family, columns in feature_sets.items():
        for classifier, variants in model_families.items():
            for variant_index, pipeline in enumerate(variants):
                expected += 1
                started = time.perf_counter()
                pipeline.fit(train[columns], train["label"])
                fit_seconds = time.perf_counter() - started
                prediction = pipeline.predict(validation[columns])
                metrics = classification_metrics(validation["label"], prediction, labels)
                rows.append({
                    "feature_family": feature_family,
                    "classifier": classifier,
                    "variant_index": variant_index,
                    "validation_macro_f1": metrics["macro_f1"],
                    "validation_balanced_accuracy": metrics["balanced_accuracy"],
                    "validation_mcc": metrics["mcc"],
                    "training_seconds": fit_seconds,
                    "parameters_json": json.dumps(jsonable_params(pipeline), sort_keys=True),
                })
    declared = json.loads(MODEL_CONFIG.read_text(encoding="utf-8"))[
        "total_candidate_budget_primary_split"
    ]
    if expected != declared:
        raise RuntimeError(f"Instantiated {expected} candidates but frozen budget is {declared}")

    leaderboard = pd.DataFrame(rows).sort_values(
        [
            "validation_macro_f1",
            "validation_balanced_accuracy",
            "validation_mcc",
            "classifier",
            "variant_index",
            "feature_family",
        ],
        ascending=[False, False, False, True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    selected_row = leaderboard.iloc[0]
    selected = {
        "task": "primary_progressive_fault_severity",
        "labels": labels,
        "split_strategy": "guard_separated_time_blocked",
        "selection_data": "training fit; validation ranking only",
        "feature_family": selected_row["feature_family"],
        "classifier": selected_row["classifier"],
        "variant_index": int(selected_row["variant_index"]),
        "validation_macro_f1": float(selected_row["validation_macro_f1"]),
        "validation_balanced_accuracy": float(selected_row["validation_balanced_accuracy"]),
        "validation_mcc": float(selected_row["validation_mcc"]),
        "parameters": json.loads(selected_row["parameters_json"]),
        "candidate_count": len(leaderboard),
        "random_state": RANDOM_STATE,
    }
    return leaderboard, selected


def save_selection(leaderboard: pd.DataFrame, selected: dict) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    leaderboard.to_csv(RESULT_DIR / "validation_leaderboard.csv", index=False)
    (RESULT_DIR / "selected_configuration_before_test.json").write_text(
        json.dumps(selected, indent=2), encoding="utf-8"
    )


def acquire_test_lock(selected: dict) -> None:
    if LOCK_FILE.exists():
        prior = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        raise RuntimeError(
            "The protected Step 12 test evaluation has already been started. "
            f"Lock status: {prior.get('status')}. Do not rerun after seeing test results."
        )
    payload = {
        "status": "STARTED",
        "purpose": "Prevent repeated confirmatory test evaluation",
        "selected_configuration_sha256": hashlib.sha256(
            json.dumps(selected, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "test_prediction_calls_permitted": 1,
    }
    # Exclusive creation prevents two processes from entering simultaneously.
    with LOCK_FILE.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def test_phase(frame: pd.DataFrame, feature_sets: dict[str, list[str]], selected: dict) -> None:
    acquire_test_lock(selected)
    columns = feature_sets[selected["feature_family"]]
    development = frame[frame["split"].isin(["train", "validation"])]
    test = frame[frame["split"] == "test"].copy()
    final_model = clone(candidates()[selected["classifier"]][selected["variant_index"]])

    started = time.perf_counter()
    final_model.fit(development[columns], development["label"])
    refit_seconds = time.perf_counter() - started
    started = time.perf_counter()
    test["prediction"] = final_model.predict(test[columns])  # the one protected call
    inference_seconds = time.perf_counter() - started

    metrics = classification_metrics(test["label"], test["prediction"], PRIMARY_LABELS)
    metrics.update({
        "refit_seconds": refit_seconds,
        "inference_seconds": inference_seconds,
        "test_windows": len(test),
        "test_blocks": int(test["block_id"].nunique()),
    })
    prediction_columns = [
        "window_hash", "run_id", "block_id", "window_start", "label", "prediction"
    ]
    test[prediction_columns].to_csv(RESULT_DIR / "test_predictions.csv", index=False)
    (RESULT_DIR / "test_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    per_class_metrics(test["label"], test["prediction"], PRIMARY_LABELS).to_csv(
        RESULT_DIR / "test_per_class_metrics.csv", index=False
    )
    confusion_matrix_frame(test["label"], test["prediction"], PRIMARY_LABELS).to_csv(
        RESULT_DIR / "test_confusion_matrix.csv"
    )
    bootstrap_draws, bootstrap_ci = stratified_block_bootstrap(
        test[["label", "prediction", "block_id"]],
        PRIMARY_LABELS,
        n_resamples=BOOTSTRAP_RESAMPLES,
        seed=RANDOM_STATE,
    )
    bootstrap_draws.to_csv(RESULT_DIR / "block_bootstrap_draws.csv", index=False)
    bootstrap_ci.to_csv(RESULT_DIR / "block_bootstrap_ci.csv", index=False)
    joblib.dump(final_model, MODEL_DIR / "step_12_primary_selected_model.joblib")

    run_record = {
        "status": "COMPLETED",
        "selected_configuration": selected,
        "test_metrics": metrics,
        "input_hashes": {
            "features": sha256(FEATURE_FILE),
            "feature_config": sha256(FEATURE_CONFIG),
            "classifier_config": sha256(MODEL_CONFIG),
            "split_audit": sha256(SPLIT_AUDIT),
        },
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
    }
    (RESULT_DIR / "run_record.json").write_text(json.dumps(run_record, indent=2), encoding="utf-8")
    lock = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    lock["status"] = "COMPLETED"
    lock["run_record_sha256"] = sha256(RESULT_DIR / "run_record.json")
    LOCK_FILE.write_text(json.dumps(lock, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--confirm-test",
        action="store_true",
        help="After validation selection, perform the one protected test evaluation.",
    )
    args = parser.parse_args()
    frame, feature_sets = load_inputs()
    leaderboard, selected = selection_phase(frame, feature_sets)
    save_selection(leaderboard, selected)
    print(json.dumps(selected, indent=2))
    if args.confirm_test:
        test_phase(frame, feature_sets, selected)
        print((RESULT_DIR / "test_metrics.json").read_text(encoding="utf-8"))
    else:
        print("Selection-only run complete. The experimental test partition was not evaluated.")
        print("Inspect validation_leaderboard.csv, then use --confirm-test exactly once.")


if __name__ == "__main__":
    main()
