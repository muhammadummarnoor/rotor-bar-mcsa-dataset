from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = PROJECT / "05_data_manifest"
FEATURES_PATH = PROJECT / "07_features" / "current_window_features.csv"
RUNS_PATH = MANIFEST_DIR / "current_run_manifest.csv"
BLOCKS_PATH = MANIFEST_DIR / "split_block_manifest.csv"
LABELS_PATH = MANIFEST_DIR / "class_label_dictionary.csv"
OUTPUT_PATH = MANIFEST_DIR / "blocked_window_manifest.csv"
AUDIT_JSON = MANIFEST_DIR / "blocked_split_leakage_audit.json"
AUDIT_MD = MANIFEST_DIR / "06_BLOCKED_SPLIT_AUDIT.md"

WINDOW = 650
EXPECTED_TOTAL = 390
EXPECTED_CLASS = {"healthy": 117, "drb_1": 156, "drb_2": 39, "drb_3": 78}
EXPECTED_CLASS_SPLIT = {
    ("healthy", "train"): 39, ("healthy", "validation"): 39, ("healthy", "test"): 39,
    ("drb_1", "train"): 52, ("drb_1", "validation"): 52, ("drb_1", "test"): 52,
    ("drb_2", "train"): 13, ("drb_2", "validation"): 13, ("drb_2", "test"): 13,
    ("drb_3", "train"): 26, ("drb_3", "validation"): 26, ("drb_3", "test"): 26,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def interval_overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return max(a0, b0) < min(a1, b1)


runs = {r["run_id"]: r for r in read_csv(RUNS_PATH)}
blocks = {b["block_id"]: b for b in read_csv(BLOCKS_PATH)}
labels = {r["code_label"]: r for r in read_csv(LABELS_PATH)}
features = read_csv(FEATURES_PATH)

rows: list[dict[str, object]] = []
errors: list[str] = []
for f in features:
    label = f["label"]
    block_id = f["block_id"]
    run_id = f["run_id"]
    if run_id not in runs:
        errors.append(f"Missing run: {run_id}")
        continue
    if block_id not in blocks:
        errors.append(f"Missing block: {block_id}")
        continue
    if label not in labels:
        errors.append(f"Missing label mapping: {label}")
        continue
    run = runs[run_id]
    block = blocks[block_id]
    lab = labels[label]
    if f["split"] != block["split"]:
        errors.append(f"Split mismatch for {block_id}: {f['split']} vs {block['split']}")
    if label != block["class_label"] or label != run["class_label"]:
        errors.append(f"Class mismatch for {block_id}")
    local_start = int(f["window_start"])
    local_end = local_start + WINDOW
    block_start = int(block["within_run_block_start"])
    block_end = int(block["within_run_block_end"])
    run_start_row = int(run["start_row"])
    within_run_start = block_start + local_start
    within_run_end = block_start + local_end
    source_start_row = run_start_row + within_run_start
    source_end_row = run_start_row + within_run_end - 1
    if local_end > block_end - block_start:
        errors.append(f"Window outside block: {block_id}@{local_start}")
    obs_key = f"{lab['paper_label']}|{run_id}|{block_id}|{within_run_start}|{within_run_end}"
    observation_id = hashlib.sha256(obs_key.encode("utf-8")).hexdigest()[:20]
    rows.append({
        "observation_id": observation_id,
        "paper_label": lab["paper_label"],
        "class_label": label,
        "ordinal_stage": int(lab["ordinal_stage"]),
        "assembly_group": lab["assembly_group"],
        "split": f["split"],
        "canonical_source_file": run["source_file"],
        "source_sha256": run["source_sha256"],
        "source_column": int(run["source_column"]),
        "run_id": run_id,
        "block_id": block_id,
        "within_block_start": local_start,
        "within_block_end_exclusive": local_end,
        "within_run_start": within_run_start,
        "within_run_end_exclusive": within_run_end,
        "source_start_row": source_start_row,
        "source_end_row_inclusive": source_end_row,
        "window_samples": WINDOW,
        "window_duration_seconds": "1.000000",
        "window_hash": f["window_hash"],
    })

fieldnames = list(rows[0])
with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

class_counts = Counter(r["class_label"] for r in rows)
class_split_counts = Counter((r["class_label"], r["split"]) for r in rows)
split_counts = Counter(r["split"] for r in rows)
block_splits: dict[str, set[str]] = defaultdict(set)
hash_splits: dict[str, set[str]] = defaultdict(set)
obs_ids = Counter(r["observation_id"] for r in rows)
for r in rows:
    block_splits[r["block_id"]].add(r["split"])
    hash_splits[r["window_hash"]].add(r["split"])

shared_blocks = {k: sorted(v) for k, v in block_splits.items() if len(v) > 1}
cross_split_hashes = {k: sorted(v) for k, v in hash_splits.items() if len(v) > 1}
duplicate_observation_ids = sorted(k for k, v in obs_ids.items() if v > 1)

cross_split_overlaps: list[dict[str, object]] = []
within_split_overlaps: list[dict[str, object]] = []
by_run: dict[str, list[dict[str, object]]] = defaultdict(list)
for r in rows:
    by_run[r["run_id"]].append(r)
for run_id, run_rows in by_run.items():
    ordered = sorted(run_rows, key=lambda x: int(x["within_run_start"]))
    for i, a in enumerate(ordered):
        for b in ordered[i + 1:]:
            if int(b["within_run_start"]) >= int(a["within_run_end_exclusive"]):
                break
            if interval_overlap(int(a["within_run_start"]), int(a["within_run_end_exclusive"]),
                                int(b["within_run_start"]), int(b["within_run_end_exclusive"])):
                item = {"run_id": run_id, "a": a["observation_id"], "b": b["observation_id"],
                        "a_split": a["split"], "b_split": b["split"]}
                (cross_split_overlaps if a["split"] != b["split"] else within_split_overlaps).append(item)

block_guard_violations: list[dict[str, object]] = []
blocks_by_run: dict[str, list[dict[str, str]]] = defaultdict(list)
for b in blocks.values():
    blocks_by_run[b["run_id"]].append(b)
for run_id, run_blocks in blocks_by_run.items():
    ordered = sorted(run_blocks, key=lambda x: int(x["within_run_block_start"]))
    for a, b in zip(ordered, ordered[1:]):
        gap = int(b["within_run_block_start"]) - int(a["within_run_block_end"])
        if gap < 650:
            block_guard_violations.append({"run_id": run_id, "a": a["block_id"], "b": b["block_id"], "gap": gap})

run_split_map = {run_id: sorted({str(r["split"]) for r in rs}) for run_id, rs in by_run.items()}
runs_present_in_multiple_splits = {k: v for k, v in run_split_map.items() if len(v) > 1}

checks = {
    "source_join_errors_zero": len(errors) == 0,
    "row_count_390": len(rows) == EXPECTED_TOTAL,
    "class_counts_match": dict(class_counts) == EXPECTED_CLASS,
    "class_split_counts_match": dict(class_split_counts) == EXPECTED_CLASS_SPLIT,
    "all_windows_650_samples": all(int(r["within_run_end_exclusive"]) - int(r["within_run_start"]) == WINDOW for r in rows),
    "all_window_durations_one_second": all(r["window_duration_seconds"] == "1.000000" for r in rows),
    "observation_ids_unique": not duplicate_observation_ids,
    "no_block_shared_across_splits": not shared_blocks,
    "no_window_hash_shared_across_splits": not cross_split_hashes,
    "no_cross_split_sample_overlap": not cross_split_overlaps,
    "no_within_split_sample_overlap": not within_split_overlaps,
    "all_interblock_guards_at_least_650": not block_guard_violations,
    "all_provenance_fields_populated": all(all(str(r[k]).strip() for k in fieldnames) for r in rows),
}
audit = {
    "protocol": {"window_samples": 650, "window_seconds": 1.0, "overlap_samples": 0,
                 "macro_block_samples": 9000, "minimum_interblock_guard_samples": 650,
                 "split_before_windowing": True},
    "counts": {"rows": len(rows), "blocks": len(blocks), "runs_with_windows": len(by_run),
               "by_class": dict(sorted(class_counts.items())), "by_split": dict(sorted(split_counts.items())),
               "by_class_split": {f"{k[0]}|{k[1]}": v for k, v in sorted(class_split_counts.items())}},
    "checks": checks,
    "audit_details": {"join_errors": errors, "shared_blocks": shared_blocks,
                      "cross_split_hashes": cross_split_hashes,
                      "cross_split_overlaps": cross_split_overlaps,
                      "within_split_overlaps": within_split_overlaps,
                      "guard_violations": block_guard_violations,
                      "duplicate_observation_ids": duplicate_observation_ids,
                      "runs_present_in_multiple_splits": runs_present_in_multiple_splits},
    "limitations": [
        "Recovered run IDs are contiguous numeric sequences, not verified physical acquisition-session IDs.",
        "The same recovered run can contribute non-overlapping guarded blocks to train, validation, and test.",
        "Passing this audit supports temporal block separation, not independent-session or cross-component generalization.",
    ],
    "all_checks_pass": all(checks.values()),
}
with AUDIT_JSON.open("w", encoding="utf-8") as f:
    json.dump(audit, f, indent=2)

status = "PASS" if audit["all_checks_pass"] else "FAIL"
md = f"""# Final Guard-Separated Time-Blocked Split Audit

**Status:** {status}  
**Generated:** 24 August 2026  
**Window manifest:** `blocked_window_manifest.csv`  
**Machine-readable audit:** `blocked_split_leakage_audit.json`

## 1. Rebuilt observation manifest

The blocked manifest contains **{len(rows)}** one-second current windows derived from **{len(blocks)}** chronological macro-blocks and **{len(by_run)}** recoverable current runs. Every observation now carries the paper label, code label, ordinal stage, assembly group, split, canonical source, source SHA-256, source column, run, block, window ranges, source-row ranges, duration, and content hash.

## 2. Counts

| Class | Train | Validation | Test | Total |
|---|---:|---:|---:|---:|
| H0 / healthy | 39 | 39 | 39 | 117 |
| F1 / drb_1 | 52 | 52 | 52 | 156 |
| F2 / drb_2 | 13 | 13 | 13 | 39 |
| F3 / drb_3 | 26 | 26 | 26 | 78 |
| **Total** | **130** | **130** | **130** | **390** |

## 3. Leakage and provenance checks

| Check | Result |
|---|---|
"""
for key, passed in checks.items():
    md += f"| {key.replace('_', ' ')} | {'PASS' if passed else 'FAIL'} |\n"
md += f"""

## 4. Important interpretation

No window range, content hash, or macro-block is shared across train, validation, and test. Adjacent macro-blocks from the same recoverable run are separated by at least 650 source samples, and each macro-block leaves an additional 550-sample unused tail after its thirteen complete windows.

However, the same recoverable numeric run can contribute different non-overlapping blocks to multiple subsets. The run IDs are not verified physical restart/session identifiers. Consequently, this is a **guard-separated time-blocked evaluation**, not an independent-session evaluation.

## 5. Step 6 decision

Step 6 is complete with status **{status}**. The manifest is suitable for the frozen time-blocked benchmark if and only if the status remains PASS after future data or code changes. Any regenerated features or splits must rerun this audit.
"""
AUDIT_MD.write_text(md, encoding="utf-8")

if not audit["all_checks_pass"]:
    raise SystemExit("Blocked split audit failed. See blocked_split_leakage_audit.json")
print(json.dumps({"status": status, "windows": len(rows), "blocks": len(blocks),
                  "output": str(OUTPUT_PATH), "audit": str(AUDIT_MD)}, indent=2))
