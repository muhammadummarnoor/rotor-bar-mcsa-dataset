# Data dictionary

## `05_data_manifest/blocked_window_manifest.csv` (390 rows, one per window)
| Column | Meaning |
|---|---|
| observation_id | Short unique window ID |
| paper_label / class_label | H0, F1, F2, F3 and the code labels healthy, drb_1, drb_2, drb_3 |
| ordinal_stage | 0 healthy, 1–3 number of drilled bars |
| assembly_group | healthy_assembly or progressive_fault_assembly |
| split | train, validation or test |
| canonical_source_file | Raw file the window was cut from (Windows-style path separators) |
| source_sha256 | SHA-256 of that raw file |
| source_column | 1-based column in the raw file |
| run_id, block_id | Capture run and 9,000-sample temporal block |
| within_block_start, within_block_end_exclusive | Sample range inside the block |
| within_run_start, within_run_end_exclusive | Sample range inside the run |
| source_start_row, source_end_row_inclusive | 1-based rows in the raw column |
| window_samples, window_duration_seconds | 650 and 1.0 (at the assumed 650 samples/s) |
| window_hash | SHA-256 of the window samples as float64 bytes; join key to the feature table |

## `07_features/current_window_features.csv`
Time domain (13 model features): std, rms, peak_abs, peak_to_peak, skewness, kurtosis, crest_factor, shape_factor,
impulse_factor, clearance_factor, median_abs_deviation, interquartile_range, energy.
Spectral (10 model features): spectral_entropy, spectral_centroid_hz, spectral_spread_hz, dominant_frequency_hz,
bandpower_0_25, bandpower_25_45, bandpower_45_55, bandpower_55_100, bandpower_100_325, fundamental_power_ratio.
The column `mean_centered` is the window mean after centring (about zero) and is not a model feature.
Plus label, split, run_id, block_id, window_start, window_hash. Definitions: `05_data_manifest/08_FROZEN_PREPROCESSING_AND_FEATURE_PROTOCOL.md`.

## `05_data_manifest/split_block_manifest.csv`
One row per temporal block: class, run, block, split, source file, column, row range, block range and `guard_samples_after` (650).

## `09_results/step_12_primary/`
`validation_leaderboard.csv` (144 configurations), `selected_configuration_before_test.json`, `test_predictions.csv`,
`test_confusion_matrix.csv`, `test_per_class_metrics.csv`, `test_metrics.json`, `block_bootstrap_ci.csv`,
`block_bootstrap_draws.csv`, `TEST_EVALUATION_LOCK.json`, `run_record.json`.
