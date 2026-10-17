from __future__ import annotations

import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = PROJECT / "05_data_manifest"
BLOCKED_PATH = MANIFEST_DIR / "blocked_window_manifest.csv"
OUTPUT_PATH = MANIFEST_DIR / "random_window_manifest.csv"
AUDIT_JSON = MANIFEST_DIR / "random_split_comparability_audit.json"
AUDIT_MD = MANIFEST_DIR / "07_RANDOM_SPLIT_BASELINE_AUDIT.md"

SEED = 20260824
SPLITS = ("train", "validation", "test")
EXPECTED_CLASS_SPLIT = {
    ("healthy", "train"): 39, ("healthy", "validation"): 39, ("healthy", "test"): 39,
    ("drb_1", "train"): 52, ("drb_1", "validation"): 52, ("drb_1", "test"): 52,
    ("drb_2", "train"): 13, ("drb_2", "validation"): 13, ("drb_2", "test"): 13,
    ("drb_3", "train"): 26, ("drb_3", "validation"): 26, ("drb_3", "test"): 26,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


blocked = read_csv(BLOCKED_PATH)
rng = random.Random(SEED)
by_class: dict[str, list[dict[str, str]]] = defaultdict(list)
for row in blocked:
    by_class[row["class_label"]].append(row)

random_split_by_id: dict[str, str] = {}
for label in sorted(by_class):
    rows = sorted(by_class[label], key=lambda r: r["observation_id"])
    rng.shuffle(rows)
    n = len(rows)
    if n % 3:
        raise SystemExit(f"Class {label} cannot be divided equally into three splits: {n}")
    size = n // 3
    for split, start in zip(SPLITS, (0, size, 2 * size)):
        for row in rows[start:start + size]:
            random_split_by_id[row["observation_id"]] = split

output_rows = []
for row in blocked:
    out = dict(row)
    out["blocked_split"] = out.pop("split")
    out["random_split"] = random_split_by_id[out["observation_id"]]
    out["random_state"] = str(SEED)
    output_rows.append(out)

fields = list(output_rows[0])
with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(output_rows)

blocked_ids = {r["observation_id"] for r in blocked}
random_ids = {r["observation_id"] for r in output_rows}
blocked_hashes = {r["window_hash"] for r in blocked}
random_hashes = {r["window_hash"] for r in output_rows}

class_random_counts = Counter((r["class_label"], r["random_split"]) for r in output_rows)
split_counts = Counter(r["random_split"] for r in output_rows)
block_random_splits: dict[str, set[str]] = defaultdict(set)
run_random_splits: dict[str, set[str]] = defaultdict(set)
for r in output_rows:
    block_random_splits[r["block_id"]].add(r["random_split"])
    run_random_splits[r["run_id"]].add(r["random_split"])

fragmented_blocks = {k: sorted(v) for k, v in block_random_splits.items() if len(v) > 1}
runs_across_splits = {k: sorted(v) for k, v in run_random_splits.items() if len(v) > 1}

adjacent_pairs_total = 0
adjacent_pairs_cross_split = 0
adjacent_examples = []
by_block: dict[str, list[dict[str, str]]] = defaultdict(list)
for r in output_rows:
    by_block[r["block_id"]].append(r)
for block_id, rows in by_block.items():
    ordered = sorted(rows, key=lambda r: int(r["within_run_start"]))
    for a, b in zip(ordered, ordered[1:]):
        if int(a["within_run_end_exclusive"]) == int(b["within_run_start"]):
            adjacent_pairs_total += 1
            if a["random_split"] != b["random_split"]:
                adjacent_pairs_cross_split += 1
                if len(adjacent_examples) < 20:
                    adjacent_examples.append({
                        "block_id": block_id,
                        "a": a["observation_id"], "a_split": a["random_split"],
                        "b": b["observation_id"], "b_split": b["random_split"],
                    })

changed_split = sum(r["blocked_split"] != r["random_split"] for r in output_rows)
checks = {
    "same_390_observation_ids": blocked_ids == random_ids and len(random_ids) == 390,
    "same_390_window_hashes": blocked_hashes == random_hashes and len(random_hashes) == 390,
    "same_class_membership": Counter(r["class_label"] for r in blocked) == Counter(r["class_label"] for r in output_rows),
    "same_provenance_rows": all(r["observation_id"] in blocked_ids for r in output_rows),
    "random_class_split_counts_match_blocked_counts": dict(class_random_counts) == EXPECTED_CLASS_SPLIT,
    "random_total_split_counts_are_130_each": dict(split_counts) == {"train": 130, "validation": 130, "test": 130},
    "deterministic_seed_recorded": all(r["random_state"] == str(SEED) for r in output_rows),
    "random_baseline_fragments_blocks_as_expected": len(fragmented_blocks) > 0,
    "random_baseline_places_adjacent_windows_across_splits": adjacent_pairs_cross_split > 0,
}

audit = {
    "random_state": SEED,
    "method": "Deterministic stratified random allocation within each class; equal one-third train, validation, and test partitions.",
    "controlled_comparison": {
        "same_windows": True, "same_window_hashes": True, "same_labels": True,
        "same_class_counts": True, "same_window_length": True,
        "intended_only_difference": "split assignment",
    },
    "counts": {
        "rows": len(output_rows), "by_random_split": dict(sorted(split_counts.items())),
        "by_class_random_split": {f"{k[0]}|{k[1]}": v for k, v in sorted(class_random_counts.items())},
        "windows_changed_relative_to_blocked_split": changed_split,
        "windows_unchanged_relative_to_blocked_split": len(output_rows) - changed_split,
        "total_blocks": len(block_random_splits), "fragmented_blocks": len(fragmented_blocks),
        "runs_present_across_random_splits": len(runs_across_splits),
        "adjacent_pairs_total": adjacent_pairs_total,
        "adjacent_pairs_crossing_random_splits": adjacent_pairs_cross_split,
        "adjacent_pair_cross_split_fraction": adjacent_pairs_cross_split / adjacent_pairs_total,
    },
    "checks": checks,
    "details": {
        "fragmented_blocks": fragmented_blocks,
        "runs_across_splits": runs_across_splits,
        "cross_split_adjacent_examples": adjacent_examples,
    },
    "interpretation": [
        "The baseline does not duplicate windows or create direct sample-range overlap because the frozen windows are non-overlapping.",
        "Its leakage risk arises from assigning temporally adjacent windows from the same macro-block and source run to different subsets.",
        "The random split is an intentionally optimistic comparator and must not replace the blocked result as the primary estimate.",
    ],
    "all_checks_pass": all(checks.values()),
}
with AUDIT_JSON.open("w", encoding="utf-8") as f:
    json.dump(audit, f, indent=2)

status = "PASS" if audit["all_checks_pass"] else "FAIL"
fraction = 100 * audit["counts"]["adjacent_pair_cross_split_fraction"]
md = f"""# Matched Random-Window Baseline and Comparability Audit

**Status:** {status}  
**Generated:** 24 August 2026  
**Random seed:** {SEED}  
**Manifest:** `random_window_manifest.csv`  
**Machine-readable audit:** `random_split_comparability_audit.json`

## 1. Purpose

This baseline uses the exact same 390 non-overlapping current windows as the guard-separated blocked benchmark. The only experimental change is subset allocation: windows are randomly shuffled within each class and assigned equally to training, validation, and test.

The random baseline is intentionally retained as an optimistic comparator. It is not the primary validation result.

## 2. Matched counts

| Class | Train | Validation | Test | Total |
|---|---:|---:|---:|---:|
| H0 / healthy | 39 | 39 | 39 | 117 |
| F1 / drb_1 | 52 | 52 | 52 | 156 |
| F2 / drb_2 | 13 | 13 | 13 | 39 |
| F3 / drb_3 | 26 | 26 | 26 | 78 |
| **Total** | **130** | **130** | **130** | **390** |

## 3. Comparability checks

| Check | Result |
|---|---|
"""
for key, passed in checks.items():
    md += f"| {key.replace('_', ' ')} | {'PASS' if passed else 'FAIL'} |\n"
md += f"""

## 4. Quantified temporal mixing

- Windows reassigned relative to the blocked split: **{changed_split} of 390**.
- Macro-blocks fragmented across two or three random subsets: **{len(fragmented_blocks)} of {len(block_random_splits)}**.
- Recoverable runs represented across random subsets: **{len(runs_across_splits)} of {len(run_random_splits)}**.
- Consecutive within-block window pairs: **{adjacent_pairs_total}**.
- Consecutive pairs separated across random subsets: **{adjacent_pairs_cross_split} ({fraction:.1f}%)**.

The random allocation does not duplicate observations and does not create direct sample overlap because the frozen windows themselves have zero overlap. Its optimism risk comes from placing neighbouring windows from the same macro-block and source recording in different subsets, allowing recording-specific temporal structure to be shared across training and evaluation.

## 5. Step 7 decision

Step 7 is complete with status **{status}**. The blocked and random experiments are matched in window identity, hashes, labels, class counts, signal duration, and provenance. Only split assignment differs, enabling a controlled estimate of random-window performance optimism.
"""
AUDIT_MD.write_text(md, encoding="utf-8")

if not audit["all_checks_pass"]:
    raise SystemExit("Random split comparability audit failed")
print(json.dumps({"status": status, "rows": len(output_rows), "changed": changed_split,
                  "fragmented_blocks": len(fragmented_blocks),
                  "cross_split_adjacent_pairs": adjacent_pairs_cross_split,
                  "output": str(OUTPUT_PATH)}, indent=2))
