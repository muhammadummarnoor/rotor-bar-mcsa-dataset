"""Step 17: robustness checks without generating new protected-test predictions."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone

from ml_metrics import PRIMARY_LABELS, classification_metrics
from step_12_primary_benchmark import candidates, load_inputs


PROJECT = Path(__file__).resolve().parents[1]
PRIMARY_DIR = PROJECT / "09_results" / "step_12_primary"
RESULT_DIR = PROJECT / "09_results" / "step_17_robustness"
SEEDS = [17, 101, 1009, 2024, 20260824]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    frame, families = load_inputs()
    selected = json.loads(
        (PRIMARY_DIR / "selected_configuration_before_test.json").read_text(encoding="utf-8")
    )
    saved_metrics = json.loads((PRIMARY_DIR / "test_metrics.json").read_text(encoding="utf-8"))
    lock = json.loads((PRIMARY_DIR / "TEST_EVALUATION_LOCK.json").read_text(encoding="utf-8"))
    predictions = pd.read_csv(PRIMARY_DIR / "test_predictions.csv")
    bootstrap_ci = pd.read_csv(PRIMARY_DIR / "block_bootstrap_ci.csv")
    bootstrap_draws = pd.read_csv(PRIMARY_DIR / "block_bootstrap_draws.csv")

    # Seed stability is validation-only: no new test predictions are produced.
    train = frame[frame["split"] == "train"]
    validation = frame[frame["split"] == "validation"]
    columns = families[selected["feature_family"]]
    seed_rows = []
    validation_predictions = []
    for seed in SEEDS:
        model = clone(candidates()[selected["classifier"]][selected["variant_index"]])
        params = model.get_params()
        if "model__random_state" in params:
            model.set_params(model__random_state=seed)
        model.fit(train[columns], train["label"])
        prediction = model.predict(validation[columns])
        metrics = classification_metrics(validation["label"], prediction, PRIMARY_LABELS)
        seed_rows.append({"seed": seed, **metrics})
        validation_predictions.append(prediction)
    seed_table = pd.DataFrame(seed_rows)
    seed_table.to_csv(RESULT_DIR / "validation_seed_stability.csv", index=False)
    prediction_matrix = np.vstack(validation_predictions)
    unanimous = (prediction_matrix == prediction_matrix[0]).all(axis=0)

    # Recompute the primary result from immutable saved predictions.
    recomputed = classification_metrics(
        predictions["label"], predictions["prediction"], PRIMARY_LABELS
    )
    metric_match = {
        metric: bool(np.isclose(recomputed[metric], saved_metrics[metric], rtol=0, atol=1e-15))
        for metric in recomputed
    }

    # Frozen most-frequent baseline: derive the class from development labels,
    # then score that constant label against the already saved test labels.
    development = frame[frame["split"].isin(["train", "validation"])]
    majority_label = development["label"].value_counts().idxmax()
    dummy_prediction = np.repeat(majority_label, len(predictions))
    dummy = classification_metrics(predictions["label"], dummy_prediction, PRIMARY_LABELS)
    dummy_comparison = pd.DataFrame([
        {"model": "most_frequent_dummy", **dummy},
        {"model": "selected_primary_model", **recomputed},
    ])
    dummy_comparison.to_csv(RESULT_DIR / "selected_vs_dummy.csv", index=False)

    # Accuracy by complete test block reveals whether errors are concentrated.
    block_rows = []
    for block_id, group in predictions.groupby("block_id", sort=True):
        block_rows.append({
            "block_id": block_id,
            "label": group["label"].iloc[0],
            "windows": len(group),
            "correct": int((group["label"] == group["prediction"]).sum()),
            "accuracy": float((group["label"] == group["prediction"]).mean()),
        })
    block_table = pd.DataFrame(block_rows)
    block_table.to_csv(RESULT_DIR / "test_block_stability.csv", index=False)

    checks = {
        "primary_test_lock_completed": lock.get("status") == "COMPLETED",
        "no_new_test_prediction_call_in_step17": True,
        "all_saved_test_metrics_reproduce": all(metric_match.values()),
        "bootstrap_draw_count_2000": len(bootstrap_draws) == 2000,
        "bootstrap_metrics_complete": set(bootstrap_ci["metric"]) == {
            "macro_f1", "balanced_accuracy", "mcc", "accuracy"
        },
        "five_validation_seeds_completed": len(seed_table) == 5,
        "all_seed_metrics_finite": bool(np.isfinite(
            seed_table.drop(columns="seed").to_numpy()
        ).all()),
        "selected_model_beats_dummy_macro_f1": recomputed["macro_f1"] > dummy["macro_f1"],
        "seven_test_blocks_present": len(block_table) == 7,
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "metric_reproduction": metric_match,
        "validation_seed_stability": {
            "seeds": SEEDS,
            "macro_f1_mean": float(seed_table["macro_f1"].mean()),
            "macro_f1_std": float(seed_table["macro_f1"].std(ddof=1)),
            "macro_f1_min": float(seed_table["macro_f1"].min()),
            "macro_f1_max": float(seed_table["macro_f1"].max()),
            "window_prediction_unanimity_fraction": float(unanimous.mean()),
        },
        "dummy_baseline": {"majority_label": majority_label, **dummy},
        "selected_primary": recomputed,
        "block_accuracy": {
            "minimum": float(block_table["accuracy"].min()),
            "median": float(block_table["accuracy"].median()),
            "maximum": float(block_table["accuracy"].max()),
        },
        "primary_artifact_hashes": {
            path.name: sha256(path) for path in [
                PRIMARY_DIR / "test_predictions.csv",
                PRIMARY_DIR / "test_metrics.json",
                PRIMARY_DIR / "block_bootstrap_ci.csv",
                PRIMARY_DIR / "TEST_EVALUATION_LOCK.json",
            ]
        },
        "interpretation_limit": (
            "Robustness is conditional on the recovered guarded blocks. It does not replace "
            "independent-session, cross-load, or cross-motor external validation."
        ),
    }
    (RESULT_DIR / "robustness_audit.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if report["status"] != "PASS":
        raise SystemExit("Step 17 robustness audit failed")


if __name__ == "__main__":
    main()
