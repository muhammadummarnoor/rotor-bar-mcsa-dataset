# Step 9 — Frozen Classifier and Hyperparameter Protocol

**Status:** Frozen before the confirmatory benchmark  
**Date:** 24 August 2026  
**Primary selection criterion:** validation macro-F1  
**Random state:** `20260824`

## Purpose

The study will compare a deliberately broad but bounded set of conventional classifiers. It will not claim to test “all known classifiers,” which is neither possible nor scientifically meaningful. The frozen suite represents linear, probabilistic, instance-based, kernel, single-tree, bagged-tree, boosted-tree, and shallow-neural-network families.

The same candidates must be used for the time-domain, MCSA/frequency-domain, and combined feature sets. The same candidates must also be used for the time-blocked and matched random-window experiments. Search spaces may not be expanded after validation or test results are viewed.

## Frozen model suite

| Model | Role/family | Scaling | Tuned values | Candidates |
|---|---|---:|---|---:|
| Dummy | Non-informative reference | No | most-frequent class | 1 |
| Logistic regression | Linear discriminative | Yes | C = 0.1, 1, 10 | 3 |
| Gaussian Naive Bayes | Probabilistic | Yes | variance smoothing = 1e-11, 1e-9, 1e-7 | 3 |
| KNN | Instance-based | Yes | neighbours = 3, 5, 9; uniform/distance weights | 6 |
| Linear SVM | Linear maximum margin | Yes | C = 0.1, 1, 10 | 3 |
| RBF SVM | Nonlinear kernel | Yes | C = 1, 10, 100; gamma = scale, 0.01 | 6 |
| Decision tree | Single tree | No | depth = 3, 6, unlimited; leaf minimum = 1, 3 | 6 |
| Random forest | Bagged randomized trees | No | depth = 6, unlimited; leaf minimum = 1, 3 | 4 |
| Extra trees | Extremely randomized trees | No | depth = 6, unlimited; leaf minimum = 1, 3 | 4 |
| Histogram gradient boosting | Boosted trees | No | learning rate = 0.05, 0.1; leaf nodes = 7, 15; L2 = 0, 1 | 8 |
| Small MLP | Shallow neural network | Yes | layers = (32) or (64,32); alpha = 0.0001 or 0.01 | 4 |

This gives **48 candidates per feature set** and **144 candidates across the three frozen feature sets** for one split strategy. The dummy reference is reported but cannot be selected as the scientific final model unless every learned classifier fails to exceed it.

## Fixed settings

- Class weighting is `balanced` for logistic regression, both SVMs, decision tree, random forest, and extra trees.
- Tree ensembles use 400 estimators and one computational job to preserve reproducibility.
- The MLP uses early stopping and a maximum of 2,000 iterations.
- SVM probability calibration is disabled because probability metrics are not part of the frozen evaluation.
- Median imputation and standardization belong inside the training pipeline; their leakage controls are frozen in Step 10.
- No resampling, SMOTE, feature selection, or post-hoc ensemble is included in this search.

## Selection and tie handling

Within each feature set, candidates are ranked using validation macro-F1 only. Exact ties are resolved in this order: validation balanced accuracy, validation MCC, alphabetic classifier name, then the lower predeclared variant index. The test set cannot participate in tuning, model-family selection, feature-set selection, or tie breaking.

## Scope exclusions

XGBoost, LightGBM, CatBoost, deep networks, and post-hoc ensembles are excluded from the confirmatory suite. With only 390 eligible primary windows, adding large external frameworks and expansive searches would increase researcher degrees of freedom without providing a fairer benchmark. LDA/QDA are also not retained in the frozen suite; Gaussian Naive Bayes provides the prespecified simple probabilistic comparator.

## Machine-readable source and verification

The authoritative search space is `frozen_classifier_search.json`. `audit_frozen_classifiers.py` checks that every declared Cartesian grid size equals the number of candidates instantiated by `train_benchmark.py`, and writes `classifier_search_audit.json`. Any later change requires a version increment and must be described as exploratory rather than confirmatory.
