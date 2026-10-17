# Matched Random-Window Baseline and Comparability Audit

**Status:** PASS  
**Generated:** 24 August 2026  
**Random seed:** 20260824  
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
| same 390 observation ids | PASS |
| same 390 window hashes | PASS |
| same class membership | PASS |
| same provenance rows | PASS |
| random class split counts match blocked counts | PASS |
| random total split counts are 130 each | PASS |
| deterministic seed recorded | PASS |
| random baseline fragments blocks as expected | PASS |
| random baseline places adjacent windows across splits | PASS |


## 4. Quantified temporal mixing

- Windows reassigned relative to the blocked split: **261 of 390**.
- Macro-blocks fragmented across two or three random subsets: **30 of 30**.
- Recoverable runs represented across random subsets: **8 of 8**.
- Consecutive within-block window pairs: **360**.
- Consecutive pairs separated across random subsets: **252 (70.0%)**.

The random allocation does not duplicate observations and does not create direct sample overlap because the frozen windows themselves have zero overlap. Its optimism risk comes from placing neighbouring windows from the same macro-block and source recording in different subsets, allowing recording-specific temporal structure to be shared across training and evaluation.

## 5. Step 7 decision

Step 7 is complete with status **PASS**. The blocked and random experiments are matched in window identity, hashes, labels, class counts, signal duration, and provenance. Only split assignment differs, enabling a controlled estimate of random-window performance optimism.
