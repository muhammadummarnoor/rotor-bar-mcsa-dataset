# Frozen Signal-Windowing Protocol

**Status:** Frozen for the primary benchmark  
**Date frozen:** 24 August 2026  
**Signal:** single-phase stator current  
**Nominal sampling frequency:** 650 Hz

## 1. Primary window definition

| Parameter | Frozen value | Interpretation |
|---|---:|---|
| Sampling frequency | 650 Hz | 650 current samples per second |
| Window length | 650 samples | 1.000 second |
| Supply frequency | 50 Hz | Reported operating supply frequency |
| Supply cycles per window | 50 cycles | 1 second x 50 Hz |
| Window stride | 650 samples | Consecutive, non-overlapping windows |
| Window overlap | 0 samples / 0% | No reused sample between adjacent primary windows |
| Macro-block length | 9000 samples | Approximately 13.846 seconds |
| Guard interval | 650 samples | One full window / one second between consecutive eligible macro-blocks |
| Windows per macro-block | 13 | 13 x 650 = 8450 modelled samples |
| Unused tail per macro-block | 550 samples | Never joined to another block or split |

The primary paper result must use this one-second, zero-overlap definition.

## 2. Justification

The 650-sample window is selected before the final benchmark because it:

1. corresponds exactly to one second at the documented 650 Hz current-sampling rate;
2. contains 50 nominal cycles of the 50 Hz supply, providing adequate frequency resolution for MCSA summary features;
3. is long enough for stable statistical and spectral estimates while remaining short enough to produce multiple windows per chronological block;
4. avoids fractional-second interpretation in the main experiment;
5. matches the existing preliminary benchmark, allowing transparent reconciliation rather than post-result window selection.

The choice is pragmatic and dataset-specific. It is not claimed to be universally optimal.

## 3. Split-before-windowing rule

Window generation must occur only after a recovered current run has been divided into chronological macro-blocks and those blocks have been assigned to train, validation, or test.

The required order is:

> canonical source -> recovered current run -> guarded chronological macro-block -> split assignment -> non-overlapping 650-sample windows -> feature extraction

The following order is prohibited:

> full recording -> windows -> random allocation of related windows to different subsets

The prohibited order is retained only for the explicitly labelled random-window optimism baseline in Step 7.

## 4. Boundary rules

1. A window must remain inside one canonical source file.
2. A window must remain inside one recovered numeric run.
3. A window must remain inside one macro-block.
4. A window must inherit exactly one class, assembly group, block ID, and split.
5. No partial final window is padded or included.
6. No unused block tail is concatenated with another block.
7. No guard sample is included in any model window.
8. No window may cross a class, run, block, or split boundary.

## 5. Observation identifiers

Every generated window must have a deterministic identifier containing or resolving to:

- class/code label;
- paper label;
- canonical source SHA-256;
- recovered run ID;
- source column;
- block ID;
- split;
- zero-based start and exclusive end index within the recovered run;
- corresponding source-row start and end;
- assembly group;
- window SHA-256 or equivalent deterministic content hash.

The exclusive end index must equal `start + 650` for every primary window.

## 6. Frozen primary window counts

| Class | Blocks | Windows per block | Total windows |
|---|---:|---:|---:|
| H0 | 9 | 13 | 117 |
| F1 | 12 | 13 | 156 |
| F2 | 3 | 13 | 39 |
| F3 | 6 | 13 | 78 |
| **Total** | **30** | **13** | **390** |

The counts reconcile exactly with the existing feature table: 390 rows.

## 7. Sensitivity protocol

Window-length sensitivity is supporting analysis, not a mechanism for replacing the frozen primary result.

Candidate lengths are:

| Samples | Duration | Nominal 50 Hz cycles | Role |
|---:|---:|---:|---|
| 325 | 0.5 s | 25 | Short-window sensitivity |
| 650 | 1.0 s | 50 | Frozen primary |
| 1300 | 2.0 s | 100 | Long-window sensitivity |

For every candidate, blocks and splits must be fixed before windows are generated. Test results must not be used to choose or redefine the primary window.

## 8. Verification requirements for Step 6

The rebuilt window manifest must demonstrate:

- every window has exactly 650 samples;
- every end index equals start plus 650;
- no within-split or cross-split sample-range overlap caused by primary windows;
- no train/validation/test pair shares a block ID;
- no content hash appears in more than one split;
- guard intervals are at least 650 samples where consecutive blocks come from the same recovered run;
- observed class totals equal H0=117, F1=156, F2=39, and F3=78;
- the split counts reconcile with the feature table and result tables.

## 9. Claims permitted by this protocol

If the verification requirements pass, the paper may state that the primary benchmark used one-second, non-overlapping current windows generated independently within guard-separated chronological partitions.

This protocol does not permit a claim of independent-session, cross-rotor, cross-motor, cross-day, or cross-load validation.

## 10. Step 5 completion decision

Step 5 is complete because the primary window length, physical duration, supply-cycle coverage, overlap, stride, macro-block length, guard interval, boundary rules, identifiers, expected counts, sensitivity candidates, and verification requirements are now frozen before the final model rerun.
