"""Frozen classification metrics and grouped uncertainty utilities.

All confirmatory experiment scripts import this module.  Do not copy metric
implementations into individual experiment files.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
)


SEED = 20260824
PRIMARY_LABELS = ["drb_1", "drb_2", "drb_3"]
SECONDARY_LABELS = ["healthy", "drb_1", "drb_2", "drb_3"]
BOOTSTRAP_RESAMPLES = 2000
CI_LEVEL = 0.95


def classification_metrics(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Sequence[str],
) -> dict[str, float]:
    """Return frozen aggregate metrics using an explicit class order."""
    return {
        "macro_f1": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "mcc": float(matthews_corrcoef(y_true, y_pred)),
        "macro_precision": float(precision_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
    }


def per_class_metrics(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Sequence[str],
) -> pd.DataFrame:
    """Return precision, recall, F1 and support for every frozen class."""
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    return pd.DataFrame({
        "label": list(labels),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "support": support.astype(int),
    })


def confusion_matrix_frame(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Sequence[str],
) -> pd.DataFrame:
    """Return an integer confusion matrix with fixed row/column labels."""
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    return pd.DataFrame(
        matrix,
        index=[f"true_{label}" for label in labels],
        columns=[f"pred_{label}" for label in labels],
    )


def stratified_block_bootstrap(
    predictions: pd.DataFrame,
    labels: Sequence[str],
    *,
    n_resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = SEED,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bootstrap complete test blocks within class and return draws plus CIs.

    Required columns: ``label``, ``prediction`` and ``block_id``.  Sampling a
    block multiple times repeats all of its windows, preserving within-block
    dependence.  Blocks are sampled separately within each true class so a
    resample cannot accidentally omit a severity class.
    """
    required = {"label", "prediction", "block_id"}
    missing = required.difference(predictions.columns)
    if missing:
        raise ValueError(f"Missing bootstrap columns: {sorted(missing)}")
    if predictions[list(required)].isna().any().any():
        raise ValueError("Bootstrap input contains missing labels, predictions, or block IDs")

    unknown = set(predictions["label"]).difference(labels)
    if unknown:
        raise ValueError(f"Unexpected true labels: {sorted(unknown)}")
    blocks_by_class = {
        label: predictions.loc[predictions["label"] == label, "block_id"].unique()
        for label in labels
    }
    empty = [label for label, blocks in blocks_by_class.items() if len(blocks) == 0]
    if empty:
        raise ValueError(f"No test blocks available for classes: {empty}")

    rng = np.random.default_rng(seed)
    draws: list[dict[str, float | int]] = []
    for draw in range(n_resamples):
        pieces = []
        for label in labels:
            blocks = blocks_by_class[label]
            sampled = rng.choice(blocks, size=len(blocks), replace=True)
            pieces.extend(
                predictions[predictions["block_id"] == block]
                for block in sampled
            )
        sample = pd.concat(pieces, ignore_index=True)
        draws.append({"resample": draw, **classification_metrics(
            sample["label"], sample["prediction"], labels
        )})

    draw_table = pd.DataFrame(draws)
    alpha = 1.0 - CI_LEVEL
    point = classification_metrics(predictions["label"], predictions["prediction"], labels)
    ci_rows = []
    for metric in ["macro_f1", "balanced_accuracy", "mcc", "accuracy"]:
        ci_rows.append({
            "metric": metric,
            "point_estimate": point[metric],
            "ci_level": CI_LEVEL,
            "ci_lower": float(draw_table[metric].quantile(alpha / 2)),
            "ci_upper": float(draw_table[metric].quantile(1 - alpha / 2)),
            "resamples": n_resamples,
            "cluster_unit": "test block, stratified by true class",
            "seed": seed,
        })
    return draw_table, pd.DataFrame(ci_rows)
