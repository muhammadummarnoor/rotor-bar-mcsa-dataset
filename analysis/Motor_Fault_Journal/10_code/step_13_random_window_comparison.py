"""Step 13: matched random-window comparator and optimism estimate."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import joblib
import pandas as pd
from sklearn.base import clone

from ml_metrics import (
    BOOTSTRAP_RESAMPLES,
    PRIMARY_LABELS,
    classification_metrics,
    confusion_matrix_frame,
    per_class_metrics,
    stratified_block_bootstrap,
)
from step_12_primary_benchmark import (
    FEATURE_CONFIG,
    MODEL_CONFIG,
    RANDOM_STATE,
    candidates,
    load_inputs,
    selection_phase,
)


PROJECT = Path(__file__).resolve().parents[1]
RANDOM_MANIFEST = PROJECT / "05_data_manifest" / "random_window_manifest.csv"
RANDOM_AUDIT = PROJECT / "05_data_manifest" / "random_split_comparability_audit.json"
BLOCKED_RESULT = PROJECT / "09_results" / "step_12_primary" / "test_metrics.json"
RESULT_DIR = PROJECT / "09_results" / "step_13_random_comparison"
MODEL_PATH = PROJECT / "08_models" / "step_13_random_selected_model.joblib"
LOCK_FILE = RESULT_DIR / "TEST_EVALUATION_LOCK.json"


def load_random_inputs() -> tuple[pd.DataFrame, dict[str, list[str]]]:
    frame, feature_sets = load_inputs()
    audit = json.loads(RANDOM_AUDIT.read_text(encoding="utf-8"))
    passed = audit.get("status") == "PASS" or audit.get("all_checks_pass") is True
    if not passed:
        raise RuntimeError("Random split comparability audit is not PASS")
    manifest = pd.read_csv(RANDOM_MANIFEST)
    mapping = manifest[["window_hash", "random_split"]].copy()
    if mapping["window_hash"].duplicated().any():
        raise ValueError("Random manifest contains duplicate window hashes")
    frame = frame.drop(columns="split").merge(mapping, on="window_hash", how="left", validate="one_to_one")
    if frame["random_split"].isna().any():
        raise ValueError("Some primary feature windows have no random-split assignment")
    frame = frame.rename(columns={"random_split": "split"})
    return frame, feature_sets


def lock_test(selected: dict) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        raise RuntimeError("Step 13 random-window test has already been evaluated; refusing rerun")
    payload = {
        "status": "STARTED",
        "test_prediction_calls_permitted": 1,
        "selected_configuration_sha256": hashlib.sha256(
            json.dumps(selected, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }
    with LOCK_FILE.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def main() -> None:
    frame, feature_sets = load_random_inputs()
    leaderboard, selected = selection_phase(frame, feature_sets)
    selected["split_strategy"] = "matched_random_window_diagnostic"
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    leaderboard.to_csv(RESULT_DIR / "validation_leaderboard.csv", index=False)
    (RESULT_DIR / "selected_configuration_before_test.json").write_text(
        json.dumps(selected, indent=2), encoding="utf-8"
    )
    lock_test(selected)

    columns = feature_sets[selected["feature_family"]]
    development = frame[frame["split"].isin(["train", "validation"])]
    test = frame[frame["split"] == "test"].copy()
    model = clone(candidates()[selected["classifier"]][selected["variant_index"]])
    started = time.perf_counter()
    model.fit(development[columns], development["label"])
    refit_seconds = time.perf_counter() - started
    started = time.perf_counter()
    test["prediction"] = model.predict(test[columns])  # one protected comparator call
    inference_seconds = time.perf_counter() - started

    random_metrics = classification_metrics(test["label"], test["prediction"], PRIMARY_LABELS)
    random_metrics.update({
        "refit_seconds": refit_seconds,
        "inference_seconds": inference_seconds,
        "test_windows": len(test),
        "test_blocks_represented": int(test["block_id"].nunique()),
        "warning": "Random-window result is diagnostic and leakage-prone by design; it is not the main generalization result."
    })
    (RESULT_DIR / "test_metrics.json").write_text(json.dumps(random_metrics, indent=2), encoding="utf-8")
    test[["window_hash", "run_id", "block_id", "window_start", "label", "prediction"]].to_csv(
        RESULT_DIR / "test_predictions.csv", index=False
    )
    per_class_metrics(test["label"], test["prediction"], PRIMARY_LABELS).to_csv(
        RESULT_DIR / "test_per_class_metrics.csv", index=False
    )
    confusion_matrix_frame(test["label"], test["prediction"], PRIMARY_LABELS).to_csv(
        RESULT_DIR / "test_confusion_matrix.csv"
    )
    draws, ci = stratified_block_bootstrap(
        test[["label", "prediction", "block_id"]], PRIMARY_LABELS,
        n_resamples=BOOTSTRAP_RESAMPLES, seed=RANDOM_STATE,
    )
    draws.to_csv(RESULT_DIR / "block_bootstrap_draws.csv", index=False)
    ci.to_csv(RESULT_DIR / "block_bootstrap_ci.csv", index=False)
    joblib.dump(model, MODEL_PATH)

    blocked = json.loads(BLOCKED_RESULT.read_text(encoding="utf-8"))
    comparison = []
    for metric in ["macro_f1", "balanced_accuracy", "mcc", "accuracy"]:
        blocked_value = float(blocked[metric])
        random_value = float(random_metrics[metric])
        comparison.append({
            "metric": metric,
            "time_blocked": blocked_value,
            "random_window": random_value,
            "random_minus_blocked": random_value - blocked_value,
            "relative_difference_percent": (
                100.0 * (random_value - blocked_value) / abs(blocked_value)
                if blocked_value != 0 else float("nan")
            ),
        })
    pd.DataFrame(comparison).to_csv(RESULT_DIR / "blocked_vs_random_comparison.csv", index=False)
    run_record = {
        "status": "COMPLETED",
        "selected_configuration": selected,
        "random_test_metrics": random_metrics,
        "warning": "Same-source neighbouring windows can cross random partitions; interpret only as an optimism diagnostic.",
        "frozen_inputs": {
            "feature_config": str(FEATURE_CONFIG),
            "classifier_config": str(MODEL_CONFIG),
            "random_manifest": str(RANDOM_MANIFEST),
        },
    }
    (RESULT_DIR / "run_record.json").write_text(json.dumps(run_record, indent=2), encoding="utf-8")
    lock = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    lock["status"] = "COMPLETED"
    LOCK_FILE.write_text(json.dumps(lock, indent=2), encoding="utf-8")
    print(json.dumps(selected, indent=2))
    print(json.dumps(random_metrics, indent=2))
    print(pd.DataFrame(comparison).to_string(index=False))


if __name__ == "__main__":
    main()
