# Step 10 — Frozen Training and Test-Isolation Protocol

**Status:** Frozen before confirmatory model training  
**Date:** 24 August 2026  
**Primary rule:** The test partition is evaluated once, after all choices are frozen.

## Confirmatory sequence

1. Use the already frozen guard-separated block assignments and features.
2. Fit every candidate pipeline using training windows only.
3. Use validation predictions to select the classifier, hyperparameters, and feature family. Test features and labels remain unopened.
4. Apply the deterministic validation tie rules in `frozen_classifier_search.json`.
5. Clone the single selected pipeline and refit it on the combined training and validation development data.
6. Generate one set of predictions for the untouched test partition.
7. Save all predictions, metrics, configuration, software versions, and hashes. Do not change the model after seeing the test result.

## Preprocessing isolation

Median imputation and, where required, standardization are pipeline steps rather than operations applied to the complete feature table. During tuning, their parameters are learned only from training windows. During the final post-selection refit, they are relearned from combined training and validation windows. They never learn from test windows.

No feature selection, PCA, SMOTE, over-sampling, under-sampling, or synthetic-data generation is allowed in the confirmatory benchmark. This keeps the number of researcher choices small and prevents transformations from being estimated before partitioning.

## Selection isolation

Validation macro-F1 is the primary selection statistic. Validation balanced accuracy and MCC are tie breakers, followed by classifier name and predeclared variant order. Test accuracy, test macro-F1, confusion matrices, and per-class test results cannot be used to select a family, variant, feature set, threshold, or random seed.

The exploratory implementation previously evaluated every selected family on the test set and included test macro-F1 as a secondary table-sort key. That behavior has been removed before the confirmatory rerun. It must not be used for the journal results.

## Split-strategy separation

The time-blocked analysis is the primary experiment. The random-window analysis is a diagnostic comparator and uses its independently frozen manifest. Model and feature search spaces remain identical, but each strategy produces its own selection and one test evaluation. Results from the random comparator cannot change the time-blocked model.

## Refit policy

After validation selection, a fresh clone of the chosen pipeline is fitted on training plus validation data. This refit does not constitute leakage because the test partition remains untouched and the configuration can no longer change. The final saved model is this development-refitted pipeline.

## Audit and remaining enforcement

`audit_training_isolation.py` checks the executable `evaluate()` path for training-only candidate fits, validation-only ranking, pipeline-contained transformations, a fresh final clone, and exactly one literal test-prediction call. Step 12 must additionally log the chosen feature set before invoking the test evaluation because the present `evaluate()` function receives one feature set at a time.
