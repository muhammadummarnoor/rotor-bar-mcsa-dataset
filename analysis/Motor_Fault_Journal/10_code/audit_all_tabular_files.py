from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re

import numpy as np
import pandas as pd


SOURCE_ROOT = Path(r"C:\Users\IT\Downloads\MSC Papers\Fyp 2018-20260820T163851Z-1-001\Fyp 2018")
OUT_DIR = Path(r"C:\Users\IT\Downloads\MSC Papers\tmp\tabular_audit")
EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".csv", ".tsv", ".ods"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_csv_robust(path: Path) -> pd.DataFrame:
    last = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin1", "utf-16"):
        try:
            return pd.read_csv(
                path, header=None, engine="python", encoding=enc,
                on_bad_lines="skip", dtype=object,
            )
        except Exception as exc:
            last = exc
    raise last


def get_sheets(path: Path):
    if path.suffix.lower() in {".csv", ".tsv"}:
        return [("CSV", read_csv_robust(path))]
    book = pd.ExcelFile(path)
    return [(name, pd.read_excel(path, sheet_name=name, header=None, dtype=object))
            for name in book.sheet_names]


def longest_true_run(mask: np.ndarray) -> int:
    if len(mask) == 0:
        return 0
    z = np.r_[False, mask, False]
    starts = np.flatnonzero(z[1:] & ~z[:-1])
    ends = np.flatnonzero(~z[1:] & z[:-1])
    return int(max(ends - starts, default=0))


def timestamp_stats(df: pd.DataFrame):
    best = {"count": 0, "column": None, "first": None, "last": None,
            "duration_s": None, "row_rate_hz": None}
    for col in df.columns[: min(6, df.shape[1])]:
        raw = df[col].astype(str).str.replace(" ->.*", "", regex=True)
        parsed = pd.to_datetime(raw, errors="coerce")
        count = int(parsed.notna().sum())
        if count <= best["count"]:
            continue
        valid = parsed.dropna()
        duration = (valid.iloc[-1] - valid.iloc[0]).total_seconds() if len(valid) > 1 else None
        rate = ((len(valid) - 1) / duration) if duration and duration > 0 else None
        best = {
            "count": count, "column": int(col) + 1,
            "first": valid.iloc[0].isoformat() if len(valid) else None,
            "last": valid.iloc[-1].isoformat() if len(valid) else None,
            "duration_s": duration, "row_rate_hz": rate,
        }
    return best


def infer_condition(rel_lower: str, text_lower: str):
    if "healty" in rel_lower or "healthy" in rel_lower:
        return "healthy"
    if "1st hole" in rel_lower or "first hole" in text_lower:
        return "one-hole"
    if "2nd hole" in rel_lower:
        return "two-hole"
    if "3rd  hole" in rel_lower or "3rd hole" in rel_lower:
        return "three-hole"
    if "second motor" in rel_lower or "second moter" in rel_lower:
        return "second-motor/unmapped"
    return "unmapped/calibration"


def analyze_sheet(path: Path, sheet_name: str, df: pd.DataFrame):
    rel = str(path.relative_to(SOURCE_ROOT))
    lower = rel.lower()
    rows, cols = df.shape
    text_sample = " ".join(
        str(x) for x in df.head(min(rows, 500)).to_numpy().ravel()
        if pd.notna(x)
    )[:30000]
    text_lower = text_sample.lower()
    numeric = df.apply(pd.to_numeric, errors="coerce")
    arr = numeric.to_numpy(dtype=float)
    finite = arr[np.isfinite(arr)]
    numeric_count = int(len(finite))
    numeric_min = float(np.min(finite)) if len(finite) else None
    numeric_max = float(np.max(finite)) if len(finite) else None

    current_cols = []
    current_max_run = 0
    low_g_cols = []
    for idx in range(cols):
        x = numeric.iloc[:, idx].to_numpy(dtype=float)
        current_mask = np.isfinite(x) & (x >= 500) & (x <= 1100)
        run = longest_true_run(current_mask)
        if run >= 500:
            current_cols.append(idx + 1)
            current_max_run = max(current_max_run, run)
        low_mask = np.isfinite(x) & (np.abs(x) <= 20)
        if int(low_mask.sum()) >= 100:
            low_g_cols.append(idx + 1)

    complete_low_g_triples = 0
    triple_columns = None
    if cols >= 3:
        for start in range(cols - 2):
            sub = numeric.iloc[:, start:start + 3].to_numpy(dtype=float)
            good = np.isfinite(sub).all(axis=1) & (np.abs(sub) <= 20).all(axis=1)
            count = int(good.sum())
            if count > complete_low_g_triples:
                complete_low_g_triples = count
                triple_columns = f"{start + 1}-{start + 3}"

    has_temperature = bool(re.search(r"temp|celsius|dht22", lower + " " + text_lower))
    has_current_text = bool(re.search(r"current|acs712|\bct\b", lower + " " + text_lower))
    has_vibration_text = bool(re.search(r"adxl|vibration|x\s*,\s*y\s*,\s*z", lower + " " + text_lower))
    has_ml_labels = bool(re.search(r"unhelathy|unhealthy|healthy|output", text_lower))
    timestamp = timestamp_stats(df)

    signals = []
    if current_cols or has_current_text:
        signals.append("current")
    if complete_low_g_triples >= 100 or has_vibration_text:
        signals.append("vibration XYZ")
    if has_temperature:
        signals.append("temperature")
    if has_ml_labels:
        signals.append("legacy labels")
    if "week schedule" in lower:
        signals = ["administrative schedule"]
    if not signals:
        signals = ["unresolved numeric/calibration"]

    condition = infer_condition(lower, text_lower)
    purpose = "Supporting/needs review"
    usability = "Do not use until mapped"
    reason = "No reliable experimental-condition mapping."

    if "week schedule" in lower:
        purpose = "Administrative"
        usability = "Exclude from modelling"
        reason = "Project schedule, not measurement data."
    elif "machine learning classifier" in lower:
        purpose = "Legacy derived ML table"
        usability = "Reference only; exclude from primary benchmark"
        reason = "Derived/labelled table includes current and temperature, not raw synchronized multisignal data."
    elif condition in {"healthy", "one-hole", "two-hole", "three-hole"}:
        purpose = "Primary condition-labelled acquisition"
        if current_cols:
            usability = "Use for current benchmark"
            reason = "Condition label is supported by filename; recoverable current-like ADC sequence present."
            if condition == "healthy" and complete_low_g_triples >= 100:
                usability = "Use current; candidate healthy XYZ after boundary verification"
                reason += " A large XYZ-like section is also present."
        else:
            usability = "Condition-labelled but no primary current run detected"
            reason = "Inspect manually before use."
    elif "second motor" in lower or "second moter" in lower:
        purpose = "Second-motor exploratory acquisition"
        usability = "External/exploratory only"
        reason = "Do not merge with the progressive single-motor classes without a separate study design."
    elif re.search(r"calib|callib|callibrate|cal |15 turn|ct-value|q2|static", lower):
        purpose = "Sensor calibration/static test"
        usability = "Calibration/supporting evidence only"
        reason = "Not a condition-labelled motor-fault acquisition."
    elif complete_low_g_triples >= 100 or "adxl" in lower or "vibration" in lower:
        purpose = "Generic/exploratory vibration acquisition"
        usability = "Do not use for supervised fault training"
        reason = "XYZ data present but no defensible progressive-fault label."
    elif "temperature" in lower:
        purpose = "Temperature experiment"
        usability = "Exclude from current-vibration model"
        reason = "Temperature is not part of the final two-signal research design."
    elif current_cols or "current" in lower or "mtotor" in lower:
        purpose = "Generic current acquisition/calibration"
        usability = "Supporting only"
        reason = "Current-like values exist but no reliable progressive-fault label."

    return {
        "relative_path": rel,
        "file_name": path.name,
        "extension": path.suffix.lower(),
        "sheet": sheet_name,
        "rows": int(rows),
        "columns": int(cols),
        "file_size_bytes": int(path.stat().st_size),
        "sha256": sha256(path),
        "condition": condition,
        "signals_detected": ", ".join(signals),
        "current_like_columns": ",".join(map(str, current_cols)),
        "longest_current_run": int(current_max_run),
        "xyz_candidate_columns": triple_columns or "",
        "complete_xyz_candidate_rows": int(complete_low_g_triples),
        "timestamp_column": timestamp["column"],
        "timestamp_count": timestamp["count"],
        "first_timestamp": timestamp["first"],
        "last_timestamp": timestamp["last"],
        "duration_seconds": timestamp["duration_s"],
        "observed_row_rate_hz": timestamp["row_rate_hz"],
        "numeric_count": numeric_count,
        "numeric_min": numeric_min,
        "numeric_max": numeric_max,
        "purpose": purpose,
        "model_use": usability,
        "reason": reason,
        "read_status": "OK",
        "read_error": "",
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = sorted(p for p in SOURCE_ROOT.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS)
    rows = []
    for path in paths:
        try:
            sheets = get_sheets(path)
            for sheet_name, df in sheets:
                rows.append(analyze_sheet(path, sheet_name, df))
        except Exception as exc:
            rows.append({
                "relative_path": str(path.relative_to(SOURCE_ROOT)),
                "file_name": path.name, "extension": path.suffix.lower(),
                "sheet": "", "rows": None, "columns": None,
                "file_size_bytes": int(path.stat().st_size), "sha256": sha256(path),
                "condition": "unknown", "signals_detected": "unreadable",
                "current_like_columns": "", "longest_current_run": None,
                "xyz_candidate_columns": "", "complete_xyz_candidate_rows": None,
                "timestamp_column": None, "timestamp_count": None,
                "first_timestamp": None, "last_timestamp": None,
                "duration_seconds": None, "observed_row_rate_hz": None,
                "numeric_count": None, "numeric_min": None, "numeric_max": None,
                "purpose": "Unreadable", "model_use": "Exclude pending recovery",
                "reason": "Parser failed.", "read_status": "ERROR",
                "read_error": f"{type(exc).__name__}: {exc}",
            })

    out = pd.DataFrame(rows)
    # Duplicate groups are based on whole-file hashes, not filenames.
    hash_counts = out.groupby("sha256")["relative_path"].transform("nunique")
    unique_hashes = sorted(out.loc[hash_counts > 1, "sha256"].unique())
    group_map = {h: f"DUP-{i+1:02d}" for i, h in enumerate(unique_hashes)}
    out["duplicate_group"] = out["sha256"].map(group_map).fillna("")
    out["is_duplicate_copy"] = hash_counts > 1
    out.to_csv(OUT_DIR / "tabular_file_audit.csv", index=False, encoding="utf-8-sig")

    # File-level summary collapses multi-sheet workbooks.
    file_summary = out.groupby(["relative_path", "sha256"], as_index=False).agg(
        sheets=("sheet", "count"), rows_max=("rows", "max"), columns_max=("columns", "max"),
        signals_detected=("signals_detected", lambda x: "; ".join(dict.fromkeys(x))),
        condition=("condition", "first"), purpose=("purpose", "first"),
        model_use=("model_use", "first"), read_status=("read_status", "first"),
        duplicate_group=("duplicate_group", "first"),
    )
    file_summary.to_csv(OUT_DIR / "file_summary.csv", index=False, encoding="utf-8-sig")

    summary = {
        "source_root": str(SOURCE_ROOT),
        "files": len(paths),
        "sheet_records": len(out),
        "read_ok": int((out.read_status == "OK").sum()),
        "read_errors": int((out.read_status != "OK").sum()),
        "unique_file_hashes": int(out.sha256.nunique()),
        "duplicate_groups": len(unique_hashes),
        "conditions": out.condition.value_counts(dropna=False).to_dict(),
        "purposes": out.purpose.value_counts(dropna=False).to_dict(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print("\nREAD ERRORS")
    print(out.loc[out.read_status != "OK", ["relative_path", "read_error"]].to_string(index=False))


if __name__ == "__main__":
    main()
