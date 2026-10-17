from pathlib import Path
import json

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, confusion_matrix,
    f1_score, matthews_corrcoef, precision_score, recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


ROOT = Path(__file__).resolve().parents[1]
FEATURE_FILE = ROOT / "07_features" / "current_window_features.csv"
TABLES = ROOT / "09_results" / "tables"
FIGURES = ROOT / "09_results" / "confusion_matrices"
CHECKS = ROOT / "09_results" / "validation_checks"
MODELS = ROOT / "08_models"
SEED = 20260824

TIME_FEATURES = [
    "std", "rms", "peak_abs", "peak_to_peak",
    "skewness", "kurtosis", "crest_factor", "shape_factor",
    "impulse_factor", "clearance_factor", "median_abs_deviation",
    "interquartile_range", "energy",
]
FREQUENCY_FEATURES = [
    "spectral_entropy", "spectral_centroid_hz", "spectral_spread_hz",
    "dominant_frequency_hz", "bandpower_0_25", "bandpower_25_45",
    "bandpower_45_55", "bandpower_55_100", "bandpower_100_325",
    "fundamental_power_ratio",
]
ALL_FEATURES = TIME_FEATURES + FREQUENCY_FEATURES
CLASS_ORDER = ["healthy", "drb_1", "drb_2", "drb_3"]


def make_model():
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("classifier", RandomForestClassifier(
            n_estimators=400, max_depth=6, min_samples_leaf=1,
            class_weight="balanced", random_state=SEED, n_jobs=1,
        )),
    ])


def scores(y_true, y_pred):
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "macro_precision": precision_score(y_true, y_pred, average="macro", zero_division=0),
        "macro_recall": recall_score(y_true, y_pred, average="macro", zero_division=0),
        "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "mcc": matthews_corrcoef(y_true, y_pred),
    }


def save_confusion(y_true, y_pred, labels, title, filename):
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    plt.figure(figsize=(6.4, 5.2))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False,
                xticklabels=labels, yticklabels=labels)
    plt.xlabel("Predicted class")
    plt.ylabel("True class")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(FIGURES / filename, dpi=300)
    plt.close()


def main():
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    CHECKS.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(FEATURE_FILE)

    train = df[df.split == "train"].copy()
    validation = df[df.split == "validation"].copy()
    test = df[df.split == "test"].copy()

    # Feature-family ablation using the same blocked partitions.
    ablation_rows = []
    for family, columns in {
        "time_domain": TIME_FEATURES,
        "frequency_domain": FREQUENCY_FEATURES,
        "combined": ALL_FEATURES,
    }.items():
        model = make_model().fit(train[columns], train.label)
        for split_name, part in [("validation", validation), ("test", test)]:
            row = {"feature_family": family, "split": split_name}
            row.update(scores(part.label, model.predict(part[columns])))
            ablation_rows.append(row)
    pd.DataFrame(ablation_rows).to_csv(TABLES / "feature_ablation.csv", index=False)

    # Binary healthy-versus-fault task.
    binary_rows = []
    binary_model = make_model()
    binary_model.fit(train[ALL_FEATURES], np.where(train.label == "healthy", "healthy", "fault"))
    for split_name, part in [("validation", validation), ("test", test)]:
        y = np.where(part.label == "healthy", "healthy", "fault")
        pred = binary_model.predict(part[ALL_FEATURES])
        row = {"split": split_name}
        row.update(scores(y, pred))
        binary_rows.append(row)
        if split_name == "test":
            save_confusion(y, pred, ["healthy", "fault"],
                           "Binary drilled-bar fault detection", "binary_random_forest.png")
    pd.DataFrame(binary_rows).to_csv(TABLES / "binary_classification.csv", index=False)
    joblib.dump(binary_model, MODELS / "binary_random_forest.joblib")

    # Blocked test compared with an intentionally leakage-prone random-window split.
    blocked_model = make_model().fit(train[ALL_FEATURES], train.label)
    blocked_pred = blocked_model.predict(test[ALL_FEATURES])
    split_rows = [{"split_strategy": "blocked", **scores(test.label, blocked_pred)}]

    random_train, random_temp = train_test_split(
        df, test_size=2/3, stratify=df.label, random_state=SEED)
    random_validation, random_test = train_test_split(
        random_temp, test_size=0.5, stratify=random_temp.label, random_state=SEED)
    random_model = make_model().fit(random_train[ALL_FEATURES], random_train.label)
    random_pred = random_model.predict(random_test[ALL_FEATURES])
    split_rows.append({"split_strategy": "random_window", **scores(random_test.label, random_pred)})
    pd.DataFrame(split_rows).to_csv(TABLES / "split_strategy_comparison.csv", index=False)
    with open(CHECKS / "random_split_warning.txt", "w", encoding="utf-8") as f:
        f.write("The random-window result is a diagnostic comparator only. It mixes windows "
                "from the same source recordings and blocks across partitions and must not be "
                "reported as the main generalization result.\n")

    # Cluster bootstrap: resample complete test blocks, preserving within-block dependence.
    rng = np.random.default_rng(SEED)
    block_ids = test.block_id.unique()
    blocks_by_class = {
        label: test.loc[test.label == label, "block_id"].unique()
        for label in CLASS_ORDER
    }
    bootstrap = []
    for _ in range(2000):
        # Stratification retains every severity class while resampling complete
        # blocks, so within-block dependence is not treated as independence.
        sampled = np.concatenate([
            rng.choice(ids, size=len(ids), replace=True)
            for ids in blocks_by_class.values()
        ])
        positions = np.concatenate([np.flatnonzero(test.block_id.to_numpy() == b) for b in sampled])
        y = test.label.to_numpy()[positions]
        pred = blocked_pred[positions]
        bootstrap.append({
            "accuracy": accuracy_score(y, pred),
            "macro_f1": f1_score(y, pred, labels=CLASS_ORDER, average="macro", zero_division=0),
            "mcc": matthews_corrcoef(y, pred),
        })
    boot_df = pd.DataFrame(bootstrap)
    point = scores(test.label, blocked_pred)
    ci_rows = []
    for metric in ["accuracy", "macro_f1", "mcc"]:
        ci_rows.append({
            "metric": metric,
            "point_estimate": point[metric],
            "ci_95_lower": boot_df[metric].quantile(0.025),
            "ci_95_upper": boot_df[metric].quantile(0.975),
            "resamples": len(boot_df),
            "cluster_unit": "test block, stratified by class",
        })
    ci = pd.DataFrame(ci_rows)
    ci.to_csv(TABLES / "block_bootstrap_ci.csv", index=False)
    boot_df.to_csv(CHECKS / "block_bootstrap_resamples.csv", index=False)
    save_confusion(test.label, blocked_pred, CLASS_ORDER,
                   "Four-class blocked test result", "extended_four_class_random_forest.png")

    metadata = {
        "seed": SEED,
        "sampling_rate_hz_assumed": 650,
        "window_samples": 650,
        "bootstrap_resamples": 2000,
        "test_blocks": int(len(block_ids)),
        "test_blocks_by_class": {k: int(len(v)) for k, v in blocks_by_class.items()},
        "test_windows": int(len(test)),
        "features": ALL_FEATURES,
    }
    (CHECKS / "extended_validation_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8")

    ci_text = "\n".join(
        f"- {r.metric}: {r.point_estimate:.3f} (95% block-bootstrap CI "
        f"{r.ci_95_lower:.3f}–{r.ci_95_upper:.3f})"
        for r in ci.itertuples()
    )
    model_card = f"""# Model Card: Progressive Drilled-Rotor-Bar Classifier

## Intended use

Preliminary comparison of healthy, one-, two-, and three-drilled-rotor-bar conditions from current-like laboratory recordings. It is a research benchmark, not a production safety or maintenance decision system.

## Input and output

- Input: 24 engineered time- and frequency-domain features from a 650-sample window.
- Output: one of `healthy`, `drb1`, `drb2`, or `drb3`.
- Selected family: balanced random forest.

## Main blocked-test uncertainty

{ci_text}

## Split controls

Complete guard-separated blocks are assigned to only one partition, and duplicate window hashes across partitions were checked. However, some blocks may originate from the same physical acquisition. The result therefore does not yet demonstrate independent-session or new-motor generalization.

## Important limitations

- The 650 Hz sampling rate is taken from archived notes and should be confirmed.
- Signal/channel identities and physical units require final experimental verification.
- The present fitted model uses recovered current-like data; it is not yet a verified current-vibration-temperature fusion model.
- Class counts are unequal, especially for the two-drilled-bar class.
- The laboratory drilled-hole faults emulate progressive bar damage and are not identical to naturally developed broken bars.
- New independent sessions, loads, days, and preferably a second motor are needed for external validation.
"""
    (MODELS / "MODEL_CARD.md").write_text(model_card, encoding="utf-8")
    print(pd.DataFrame(ablation_rows).to_string(index=False))
    print("\nBinary results\n", pd.DataFrame(binary_rows).to_string(index=False))
    print("\nSplit comparison\n", pd.DataFrame(split_rows).to_string(index=False))
    print("\nConfidence intervals\n", ci.to_string(index=False))


if __name__ == "__main__":
    main()
