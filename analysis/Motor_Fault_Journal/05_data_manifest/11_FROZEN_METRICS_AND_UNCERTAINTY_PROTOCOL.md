# Step 11 — Frozen Metrics and Uncertainty Protocol

**Status:** Frozen before confirmatory model execution  
**Date:** 24 August 2026

## Tasks and class order

The primary progressive-fault task contains `drb_1`, `drb_2`, and `drb_3`, in that order. Healthy data are excluded from this primary severity classifier. The secondary four-class task uses `healthy`, `drb_1`, `drb_2`, and `drb_3`, in that order, and must retain the documented assembly-confounding limitation.

## Metrics

Validation macro-F1 is the sole primary model-selection statistic. Test macro-F1 is the primary reported performance metric because the three drilled-fault classes have unequal window counts. Supporting aggregate metrics are balanced accuracy, Matthews correlation coefficient, macro precision, macro recall, and accuracy. Precision, recall, F1 and support are also reported for every class, together with a fixed-order confusion matrix.

Undefined precision or recall is assigned zero. This rule prevents omitted predictions for a difficult class from producing missing or artificially favourable macro scores. Training and inference times are descriptive diagnostics, not selection statistics.

## Uncertainty

The test uncertainty analysis uses 2,000 nonparametric percentile-bootstrap resamples with random state `20260824`. Complete test blocks—not individual one-second windows—are resampled because windows from the same block are dependent. Resampling is stratified by true class so each draw retains every severity class. Ninety-five-percent intervals are produced for macro-F1, balanced accuracy, MCC and accuracy.

Because only a small number of independent blocks is available, the intervals describe block-level sampling variability within this experiment; they do not establish population-level generalization to new motors, loads, laboratories, or fault constructions.

## Single implementation

All experiment scripts must import metric calculations from `10_code/ml_metrics.py`. `step_11_verify_metrics.py` tests class ordering, finite outputs, confusion-matrix dimensions and deterministic block-bootstrap behaviour using synthetic data only; it does not open the experimental test partition.
