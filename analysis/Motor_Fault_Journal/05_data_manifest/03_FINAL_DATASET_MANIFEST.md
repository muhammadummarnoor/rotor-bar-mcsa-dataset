# Final Dataset Manifest and Inclusion Decision

**Status:** Frozen for the current-only benchmark  
**Date frozen:** 24 August 2026  
**Machine-readable table:** `final_dataset_manifest.csv`

## 1. Final dataset scope

The supervised benchmark is restricted to four canonical, condition-labelled source files containing single-phase stator-current measurements at a documented nominal sampling rate of 650 Hz.

The primary task uses F1, F2, and F3. The healthy H0 class is retained only for the secondary four-class analysis because it was measured using a different intact rotor-shaft-bearing assembly.

Raw vibration is not part of this frozen modelling dataset. Healthy X-Y-Z values exist, but corresponding condition-labelled F1/F2/F3 vibration files cannot be mapped defensibly.

## 2. Canonical source files

| Code | Physical condition | Canonical source | SHA-256 verified | Primary task | Secondary task |
|---|---|---|---|---|---|
| H0 | Healthy/intact rotor | `04_raw_data/healthy/healthy_2022-02-17.csv` | Yes | No | Yes, with assembly warning |
| F1 | One partially drilled rotor bar | `04_raw_data/drb_1/drb1_2022-03-04.xlsx` | Yes | Yes | Yes |
| F2 | Two partially drilled rotor bars | `04_raw_data/drb_2/drb2_2022-03-04.csv` | Yes | Yes | Yes |
| F3 | Three partially drilled rotor bars | `04_raw_data/drb_3/drb3_2022-03-04.csv` | Yes | Yes | Yes |

The hashes in `final_dataset_manifest.csv` match the current project files and the earlier run manifest. Exact duplicate archive copies are excluded and must never be counted as independent recordings.

## 3. Recoverable current material

| Code | Detected current-like runs | Complete runs | Detected samples | Samples entering 9000-sample blocks | Blocks | One-second windows |
|---|---:|---:|---:|---:|---:|---:|
| H0 | 1 | 1 | 92,241 | 81,000 | 9 | 117 |
| F1 | 5 | 4 | 126,289 | 108,000 | 12 | 156 |
| F2 | 1 | 1 | 29,975 | 27,000 | 3 | 39 |
| F3 | 2 | 2 | 59,961 | 54,000 | 6 | 78 |
| **Total** | **9** | **8** | **308,466** | **270,000** | **30** | **390** |

Each guarded block contains 9000 current samples. One-second non-overlapping windows contain 650 samples, producing 13 windows per block; the remaining block tail is not windowed. A 650-sample guard follows eligible blocks where the source run permits it.

The additional F1 run of 6385 samples is visible in the run manifest but is shorter than the frozen 9000-sample block length. It therefore contributes no block or model window and is effectively excluded without a special-case rule.

## 4. Date and timestamp evidence

| Code | Best date evidence | Sample-level timestamp status |
|---|---|---|
| H0 | 17 February 2022 from the source name and archived metadata | No timestamps stored with the samples |
| F1 | 4 March 2022 confirmed by Excel properties and source metadata | Time-of-day values approximately 15:17:12.197-15:20:17.701; insufficient for session grouping |
| F2 | 4 March 2022 from source name and archived metadata | No usable timestamps |
| F3 | 4 March 2022 supported by the preferred original copy metadata | Time-of-day values approximately 15:15:12-15:18:41; insufficient for session grouping |

The clock intervals for F1 and F3 overlap even though the physical stages could not be tested simultaneously. These time-only values must not be used to reconstruct experimental order or independent sessions.

## 5. Class and assembly definitions

- **H0:** intact healthy condition measured with a separate but same-model/dimensions rotor-shaft-bearing assembly.
- **F1:** one partial hole introduced in one rotor bar.
- **F2:** a second partial hole introduced in an adjacent bar, axially offset downward from the first hole.
- **F3:** a third bar damaged approximately 180 degrees around the rotor circumference.

F1, F2, and F3 belong to the same progressively modified rotor-shaft-bearing assembly. The body/stator, sensor arrangement, measured current channel, supply condition, and fixed mechanical-load arrangement were kept the same according to the experimental record and experimenter confirmation.

## 6. Inclusion rules

### Included

1. Current-like numeric sequences between the established ADC-like bounds used by the extraction code.
2. Canonical H0/F1/F2/F3 files listed above.
3. Complete 9000-sample chronological blocks produced without crossing a detected numeric-run boundary.
4. One-second, 650-sample windows generated inside an assigned block.

### Excluded

1. Exact duplicate file copies.
2. Calibration and static sensor trials.
3. Generic or second-motor acquisitions without progressive-condition labels.
4. Temperature columns.
5. Unmapped vibration recordings.
6. Short material that cannot form a complete frozen block.
7. Values outside recoverable current-like runs and incomplete window tails.

## 7. Known imbalance

The frozen block-eligible dataset is imbalanced: F1 has 156 windows, F3 has 78, and F2 has 39. This imbalance is a property of the recoverable complete data and must not be hidden by duplicating test observations.

Required responses are:

- use macro-F1, balanced accuracy, MCC, and per-class metrics;
- apply any class weighting or resampling to training data only;
- preserve the natural validation and test composition;
- report the class counts beside all main results.

## 8. Independence limitation

The run and block identifiers describe recoverable contiguous numeric sequences and chronological partitions. They are not verified physical acquisition-session identifiers. The manifest supports time-blocked evaluation but does not support a claim of independent-session testing.

## 9. Step 3 completion decision

Step 3 is complete because:

- exactly four canonical condition-labelled current sources are frozen;
- their SHA-256 hashes are verified;
- duplicate copies and non-model signals are excluded;
- current runs, samples, blocks, windows, dates, timestamps, assemblies, and class roles are documented;
- the primary and secondary datasets are explicitly separated;
- imbalance and independence limitations are recorded before further modelling.
