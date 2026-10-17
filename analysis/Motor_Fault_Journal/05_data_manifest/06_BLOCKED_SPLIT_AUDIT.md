# Final Guard-Separated Time-Blocked Split Audit

**Status:** PASS  
**Generated:** 24 August 2026  
**Window manifest:** `blocked_window_manifest.csv`  
**Machine-readable audit:** `blocked_split_leakage_audit.json`

## 1. Rebuilt observation manifest

The blocked manifest contains **390** one-second current windows derived from **30** chronological macro-blocks and **8** recoverable current runs. Every observation now carries the paper label, code label, ordinal stage, assembly group, split, canonical source, source SHA-256, source column, run, block, window ranges, source-row ranges, duration, and content hash.

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
| source join errors zero | PASS |
| row count 390 | PASS |
| class counts match | PASS |
| class split counts match | PASS |
| all windows 650 samples | PASS |
| all window durations one second | PASS |
| observation ids unique | PASS |
| no block shared across splits | PASS |
| no window hash shared across splits | PASS |
| no cross split sample overlap | PASS |
| no within split sample overlap | PASS |
| all interblock guards at least 650 | PASS |
| all provenance fields populated | PASS |


## 4. Important interpretation

No window range, content hash, or macro-block is shared across train, validation, and test. Adjacent macro-blocks from the same recoverable run are separated by at least 650 source samples, and each macro-block leaves an additional 550-sample unused tail after its thirteen complete windows.

However, the same recoverable numeric run can contribute different non-overlapping blocks to multiple subsets. The run IDs are not verified physical restart/session identifiers. Consequently, this is a **guard-separated time-blocked evaluation**, not an independent-session evaluation.

## 5. Step 6 decision

Step 6 is complete with status **PASS**. The manifest is suitable for the frozen time-blocked benchmark if and only if the status remains PASS after future data or code changes. Any regenerated features or splits must rerun this audit.
