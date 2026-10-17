"""Step 16: secondary H0/F1/F2/F3 analysis with confounding disclosure."""
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
    SECONDARY_LABELS,
    classification_metrics,
    confusion_matrix_frame,
    per_class_metrics,
    stratified_block_bootstrap,
)
from step_12_primary_benchmark import candidates, load_inputs, selection_phase


PROJECT = Path(__file__).resolve().parents[1]
FEATURE_FILE = PROJECT / "07_features" / "current_window_features.csv"
FEATURE_CONFIG = PROJECT / "05_data_manifest" / "frozen_feature_sets.json"
RESULT_DIR = PROJECT / "09_results" / "step_16_secondary_four_class"
MODEL_PATH = PROJECT / "08_models" / "step_16_secondary_four_class_model.joblib"
LOCK_FILE = RESULT_DIR / "TEST_EVALUATION_LOCK.json"
WARNING = (
    "ASSEMBLY-CONFOUNDING WARNING: H0 used a different rotor-shaft-bearing assembly "
    "from the drilled-fault conditions. Therefore healthy-versus-fault discrimination "
    "may reflect assembly identity as well as rotor-bar condition. This secondary "
    "four-class result is not evidence of assembly-independent fault detection."
)


def load_secondary() -> tuple[pd.DataFrame, dict[str, list[str]]]:
    # Reuse frozen feature definitions and leakage-audit gate, then restore H0
    # because load_inputs intentionally filters it from the primary task.
    _, families = load_inputs()
    frame = pd.read_csv(FEATURE_FILE)
    frame = frame[frame["label"].isin(SECONDARY_LABELS)].copy()
    if set(frame["label"]) != set(SECONDARY_LABELS):
        raise ValueError("Secondary table does not contain H0/F1/F2/F3")
    if set(frame["split"]) != {"train", "validation", "test"}:
        raise ValueError("Secondary table lacks a frozen partition")
    return frame, families


def acquire_lock(selected: dict) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        raise RuntimeError("Step 16 protected secondary test has already been evaluated")
    payload = {
        "status": "STARTED",
        "test_prediction_calls_permitted": 1,
        "warning": WARNING,
        "selected_configuration_sha256": hashlib.sha256(
            json.dumps(selected, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }
    with LOCK_FILE.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def main() -> None:
    frame, families = load_secondary()
    leaderboard, selected = selection_phase(frame, families, labels=SECONDARY_LABELS)
    selected.update({
        "task": "secondary_H0_F1_F2_F3",
        "status": "secondary_due_to_assembly_confounding",
        "mandatory_warning": WARNING,
    })
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    leaderboard["mandatory_warning"] = WARNING
    leaderboard.to_csv(RESULT_DIR / "validation_leaderboard.csv", index=False)
    (RESULT_DIR / "selected_configuration_before_test.json").write_text(
        json.dumps(selected, indent=2), encoding="utf-8"
    )
    (RESULT_DIR / "ASSEMBLY_CONFOUNDING_WARNING.txt").write_text(WARNING + "\n", encoding="utf-8")
    acquire_lock(selected)

    columns = families[selected["feature_family"]]
    development = frame[frame["split"].isin(["train", "validation"])]
    test = frame[frame["split"] == "test"].copy()
    model = clone(candidates()[selected["classifier"]][selected["variant_index"]])
    started = time.perf_counter()
    model.fit(development[columns], development["label"])
    refit_seconds = time.perf_counter() - started
    started = time.perf_counter()
    test["prediction"] = model.predict(test[columns])  # one protected call
    inference_seconds = time.perf_counter() - started

    metrics = classification_metrics(test["label"], test["prediction"], SECONDARY_LABELS)
    metrics.update({
        "test_windows": len(test),
        "test_blocks": int(test["block_id"].nunique()),
        "refit_seconds": refit_seconds,
        "inference_seconds": inference_seconds,
        "mandatory_warning": WARNING,
    })
    (RESULT_DIR / "test_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    test[["window_hash", "run_id", "block_id", "window_start", "label", "prediction"]].to_csv(
        RESULT_DIR / "test_predictions.csv", index=False
    )
    per_class = per_class_metrics(test["label"], test["prediction"], SECONDARY_LABELS)
    per_class["mandatory_warning"] = WARNING
    per_class.to_csv(RESULT_DIR / "test_per_class_metrics.csv", index=False)
    confusion_matrix_frame(test["label"], test["prediction"], SECONDARY_LABELS).to_csv(
        RESULT_DIR / "test_confusion_matrix.csv"
    )
    draws, ci = stratified_block_bootstrap(
        test[["label", "prediction", "block_id"]], SECONDARY_LABELS,
        n_resamples=BOOTSTRAP_RESAMPLES,
    )
    draws.to_csv(RESULT_DIR / "block_bootstrap_draws.csv", index=False)
    ci["mandatory_warning"] = WARNING
    ci.to_csv(RESULT_DIR / "block_bootstrap_ci.csv", index=False)
    joblib.dump(model, MODEL_PATH)

    record = {
        "status": "COMPLETED",
        "role": "secondary analysis only",
        "selected_configuration": selected,
        "test_metrics": metrics,
        "mandatory_warning": WARNING,
    }
    (RESULT_DIR / "run_record.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    lock = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    lock["status"] = "COMPLETED"
    LOCK_FILE.write_text(json.dumps(lock, indent=2), encoding="utf-8")
    print(WARNING)
    print(json.dumps(selected, indent=2))
    print(json.dumps(metrics, indent=2))
    print(per_class.drop(columns="mandatory_warning").to_string(index=False))


if __name__ == "__main__":
    main()
