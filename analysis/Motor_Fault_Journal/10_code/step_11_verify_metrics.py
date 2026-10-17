"""Step 11: verify the frozen metrics and uncertainty implementation."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ml_metrics import (
    PRIMARY_LABELS,
    classification_metrics,
    confusion_matrix_frame,
    per_class_metrics,
    stratified_block_bootstrap,
)


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT / "05_data_manifest" / "metric_implementation_audit.json"


def main() -> None:
    # A deterministic synthetic example exercises every metric and the block
    # bootstrap without opening any experimental test labels.
    truth = np.repeat(PRIMARY_LABELS, 4)
    prediction = np.array([
        "drb_1", "drb_1", "drb_2", "drb_1",
        "drb_2", "drb_2", "drb_2", "drb_3",
        "drb_3", "drb_3", "drb_1", "drb_3",
    ])
    block = np.repeat(["f1_a", "f1_b", "f2_a", "f2_b", "f3_a", "f3_b"], 2)
    table = pd.DataFrame({"label": truth, "prediction": prediction, "block_id": block})

    aggregate = classification_metrics(truth, prediction, PRIMARY_LABELS)
    classes = per_class_metrics(truth, prediction, PRIMARY_LABELS)
    matrix = confusion_matrix_frame(truth, prediction, PRIMARY_LABELS)
    draws_a, ci_a = stratified_block_bootstrap(table, PRIMARY_LABELS, n_resamples=100, seed=17)
    draws_b, ci_b = stratified_block_bootstrap(table, PRIMARY_LABELS, n_resamples=100, seed=17)

    checks = {
        "primary_macro_f1_present": "macro_f1" in aggregate,
        "all_aggregate_metrics_finite": bool(np.isfinite(list(aggregate.values())).all()),
        "per_class_order_fixed": classes["label"].tolist() == PRIMARY_LABELS,
        "confusion_shape_correct": list(matrix.shape) == [3, 3],
        "bootstrap_has_100_draws": len(draws_a) == 100,
        "bootstrap_is_seed_reproducible": draws_a.equals(draws_b) and ci_a.equals(ci_b),
        "ci_bounds_ordered": bool((ci_a["ci_lower"] <= ci_a["point_estimate"]).all()
                                  and (ci_a["point_estimate"] <= ci_a["ci_upper"]).all()),
        "synthetic_only_no_experimental_test_opened": True,
    }
    audit = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "synthetic_aggregate_metrics": aggregate,
    }
    OUTPUT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))
    if audit["status"] != "PASS":
        raise SystemExit("Metric implementation audit failed")


if __name__ == "__main__":
    main()
