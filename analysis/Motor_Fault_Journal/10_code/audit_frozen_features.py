from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
FEATURE_PATH = PROJECT / "07_features" / "current_window_features.csv"
CONFIG_PATH = PROJECT / "05_data_manifest" / "frozen_feature_sets.json"
AUDIT_PATH = PROJECT / "05_data_manifest" / "feature_table_audit.json"

df = pd.read_csv(FEATURE_PATH)
config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
time_features = config["time_domain"]
frequency_features = config["frequency_domain"]
model_features = time_features + frequency_features
metadata = ["label", "split", "run_id", "block_id", "window_start", "window_hash"]
numeric_extracted = [c for c in df.columns if c not in metadata]

duplicate_columns = []
for i, a in enumerate(model_features):
    for b in model_features[i + 1:]:
        if df[a].equals(df[b]):
            duplicate_columns.append([a, b])

checks = {
    "rows_390": len(df) == 390,
    "all_frozen_features_present": set(model_features).issubset(df.columns),
    "time_feature_count_13": len(time_features) == 13,
    "frequency_feature_count_10": len(frequency_features) == 10,
    "combined_feature_count_23": len(model_features) == 23,
    "no_missing_model_values": int(df[model_features].isna().sum().sum()) == 0,
    "no_infinite_model_values": int(np.isinf(df[model_features].to_numpy()).sum()) == 0,
    "no_constant_model_features": all(df[c].nunique(dropna=False) > 1 for c in model_features),
    "no_exact_duplicate_model_columns": len(duplicate_columns) == 0,
    "mean_centered_excluded": "mean_centered" not in model_features,
    "all_window_hashes_unique": df["window_hash"].nunique() == len(df),
}

ranges = {
    c: {"min": float(df[c].min()), "max": float(df[c].max()),
        "unique_values": int(df[c].nunique(dropna=False))}
    for c in numeric_extracted
}
audit = {
    "feature_file": str(FEATURE_PATH.relative_to(PROJECT)),
    "rows": len(df),
    "numeric_features_extracted": len(numeric_extracted),
    "frozen_model_features": len(model_features),
    "time_features": time_features,
    "frequency_features": frequency_features,
    "excluded_features": config["excluded"],
    "missing_cells_in_frozen_features": int(df[model_features].isna().sum().sum()),
    "infinite_cells_in_frozen_features": int(np.isinf(df[model_features].to_numpy()).sum()),
    "constant_model_features": [c for c in model_features if df[c].nunique(dropna=False) <= 1],
    "duplicate_model_columns": duplicate_columns,
    "ranges": ranges,
    "checks": checks,
    "all_checks_pass": all(checks.values()),
    "cautions": [
        "std and rms, and energy and rms, are mathematically related; they are retained for transparent conventional-feature benchmarking, not interpreted as independent physical mechanisms.",
        "Band powers are in squared ADC/FFT units because a verified current calibration equation is unavailable.",
        "The 1 Hz FFT resolution and absent synchronized RPM do not support exact per-window slip-sideband tracking.",
        "Feature importance must not be interpreted causally in the presence of correlated predictors."
    ]
}
AUDIT_PATH.write_text(json.dumps(audit, indent=2), encoding="utf-8")
if not audit["all_checks_pass"]:
    raise SystemExit("Frozen feature audit failed")
print(json.dumps({"status": "PASS", "rows": len(df), "extracted": len(numeric_extracted),
                  "frozen": len(model_features), "time": len(time_features),
                  "frequency": len(frequency_features), "audit": str(AUDIT_PATH)}, indent=2))
