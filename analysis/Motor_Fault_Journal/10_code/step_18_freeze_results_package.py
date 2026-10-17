"""Step 18: reconcile, visualize, hash, and freeze the final result package."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from ml_metrics import PRIMARY_LABELS, SECONDARY_LABELS, classification_metrics


PROJECT = Path(__file__).resolve().parents[1]
RESULTS = PROJECT / "09_results"
PACKAGE = RESULTS / "final_package"
FIGURES = PACKAGE / "figures"
TABLES = PACKAGE / "tables"
MANIFEST = PACKAGE / "artifact_manifest.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def confusion_figure(csv_path: Path, title: str, output: Path, labels: list[str], warning: str | None = None) -> None:
    frame = pd.read_csv(csv_path, index_col=0)
    frame.index = labels
    frame.columns = labels
    plt.figure(figsize=(6.2, 5.2 if warning is None else 5.8))
    sns.heatmap(frame, annot=True, fmt="d", cmap="Blues", cbar=False)
    plt.xlabel("Predicted class")
    plt.ylabel("True class")
    plt.title(title)
    if warning:
        plt.figtext(0.5, 0.01, warning, ha="center", va="bottom", fontsize=7, wrap=True)
        plt.tight_layout(rect=(0, 0.12, 1, 1))
    else:
        plt.tight_layout()
    plt.savefig(output, dpi=300)
    plt.close()


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    s12 = RESULTS / "step_12_primary"
    s13 = RESULTS / "step_13_random_comparison"
    s14 = RESULTS / "step_14_feature_ablation"
    s15 = RESULTS / "step_15_window_sensitivity"
    s16 = RESULTS / "step_16_secondary_four_class"
    s17 = RESULTS / "step_17_robustness"

    required_locks = [
        s12 / "TEST_EVALUATION_LOCK.json",
        s13 / "TEST_EVALUATION_LOCK.json",
        s14 / "TEST_EVALUATION_LOCK.json",
        s15 / "TEST_EVALUATION_LOCK.json",
        s16 / "TEST_EVALUATION_LOCK.json",
    ]
    lock_checks = {str(path.relative_to(PROJECT)): load_json(path).get("status") == "COMPLETED"
                   for path in required_locks}

    primary_metrics = load_json(s12 / "test_metrics.json")
    primary_pred = pd.read_csv(s12 / "test_predictions.csv")
    recomputed = classification_metrics(primary_pred["label"], primary_pred["prediction"], PRIMARY_LABELS)
    primary_metric_checks = {
        key: bool(np.isclose(value, primary_metrics[key], rtol=0, atol=1e-15))
        for key, value in recomputed.items()
    }
    random_metrics = load_json(s13 / "test_metrics.json")
    ablation = pd.read_csv(s14 / "feature_family_ablation.csv")
    sensitivity = pd.read_csv(s15 / "window_length_sensitivity.csv")
    secondary_metrics = load_json(s16 / "test_metrics.json")
    robustness = load_json(s17 / "robustness_audit.json")
    primary_ci = pd.read_csv(s12 / "block_bootstrap_ci.csv")
    secondary_ci = pd.read_csv(s16 / "block_bootstrap_ci.csv")

    # Final publication tables copied from immutable result artifacts.
    summary = {
        "primary_three_fault_task": {
            "selected_model": "ExtraTrees",
            "selected_features": "combined",
            **{k: primary_metrics[k] for k in ["macro_f1", "balanced_accuracy", "mcc", "accuracy"]},
            "macro_f1_ci_95": primary_ci.loc[primary_ci.metric == "macro_f1", ["ci_lower", "ci_upper"]].iloc[0].tolist(),
            "test_windows": primary_metrics["test_windows"],
            "test_blocks": primary_metrics["test_blocks"],
        },
        "random_window_diagnostic": {
            **{k: random_metrics[k] for k in ["macro_f1", "balanced_accuracy", "mcc", "accuracy"]},
            "macro_f1_minus_blocked": random_metrics["macro_f1"] - primary_metrics["macro_f1"],
            "warning": random_metrics["warning"],
        },
        "feature_ablation": ablation[["feature_family", "classifier", "macro_f1", "balanced_accuracy", "mcc"]].to_dict("records"),
        "window_sensitivity": sensitivity[["window_samples", "selected_feature_family", "selected_classifier", "macro_f1"]].to_dict("records"),
        "secondary_four_class": {
            **{k: secondary_metrics[k] for k in ["macro_f1", "balanced_accuracy", "mcc", "accuracy"]},
            "macro_f1_ci_95": secondary_ci.loc[secondary_ci.metric == "macro_f1", ["ci_lower", "ci_upper"]].iloc[0].tolist(),
            "mandatory_warning": secondary_metrics["mandatory_warning"],
        },
    }
    (PACKAGE / "final_results_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    claim_evidence = {
        "C1": {"status": "Supported", "evidence": "Primary macro-F1 0.9065 (95% block-bootstrap CI 0.8338-0.9835), balanced accuracy 0.9295, MCC 0.8572."},
        "C2": {"status": "Supported", "evidence": "Random-window macro-F1 1.0000 versus blocked 0.9065; absolute increase 0.0935."},
        "C3": {"status": "Supported", "evidence": "Frequency-only macro-F1 0.9748 versus time-only 0.7350 under the prespecified ablation."},
        "C4": {"status": "Not supported", "evidence": "Combined macro-F1 0.9065 was lower than frequency-only 0.9748."},
        "C5": {"status": "Not supported", "evidence": "Extra Trees was validation-selected, but an accuracy-complexity trade-off was not formally optimized; frequency-only HGB scored higher in the supporting test ablation."},
        "C6": {"status": "Supported", "evidence": "C1 performance was obtained using the documented low-cost single-phase current acquisition arrangement; scope is fixed-load feasibility only."},
        "C7": {"status": "Supported with mandatory limitation", "evidence": "Secondary macro-F1 0.9367 (95% CI 0.8886-0.9876), with healthy-versus-fault separation confounded by assembly identity."},
    }
    (PACKAGE / "claim_evidence_audit.json").write_text(json.dumps(claim_evidence, indent=2), encoding="utf-8")

    # Figures generated only from frozen CSV/JSON artifacts.
    confusion_figure(s12 / "test_confusion_matrix.csv", "Primary time-blocked F1/F2/F3 test", FIGURES / "primary_confusion_matrix.png", ["F1", "F2", "F3"])
    warning_short = "H0 used a different rotor–shaft–bearing assembly; four-class interpretation is assembly-confounded."
    confusion_figure(s16 / "test_confusion_matrix.csv", "Secondary H0/F1/F2/F3 test", FIGURES / "secondary_confusion_matrix.png", ["H0", "F1", "F2", "F3"], warning_short)

    comparison = pd.read_csv(s13 / "blocked_vs_random_comparison.csv")
    macro = comparison[comparison.metric == "macro_f1"].iloc[0]
    plt.figure(figsize=(5.8, 4.4))
    sns.barplot(x=["Time-blocked", "Random-window"], y=[macro.time_blocked, macro.random_window], hue=["Time-blocked", "Random-window"], legend=False, palette=["#2878B5", "#D9534F"])
    plt.ylim(0, 1.05); plt.ylabel("Test macro-F1"); plt.xlabel("")
    plt.title("Split-strategy comparison")
    plt.figtext(0.5, 0.01, "Random-window result is a leakage-prone diagnostic.", ha="center", fontsize=8)
    plt.tight_layout(rect=(0, 0.05, 1, 1)); plt.savefig(FIGURES / "split_strategy_macro_f1.png", dpi=300); plt.close()

    plt.figure(figsize=(6.4, 4.5))
    order = ["time_domain", "frequency_domain", "combined"]
    plot = ablation.set_index("feature_family").loc[order].reset_index()
    plot["feature_family"] = ["Time-domain", "Frequency-domain", "Combined"]
    sns.barplot(data=plot, x="feature_family", y="macro_f1", color="#2878B5")
    plt.ylim(0, 1.05); plt.xlabel("Feature family"); plt.ylabel("Test macro-F1"); plt.title("Feature-family ablation")
    plt.tight_layout(); plt.savefig(FIGURES / "feature_ablation_macro_f1.png", dpi=300); plt.close()

    plt.figure(figsize=(6.4, 4.5))
    sns.lineplot(data=sensitivity, x="window_samples", y="macro_f1", marker="o", color="#2878B5")
    plt.ylim(0, 1.05); plt.xlabel("Window length (samples)"); plt.ylabel("Test macro-F1"); plt.title("Window-length sensitivity")
    plt.tight_layout(); plt.savefig(FIGURES / "window_sensitivity_macro_f1.png", dpi=300); plt.close()

    source_tables = {
        "primary_test_metrics.json": s12 / "test_metrics.json",
        "primary_per_class.csv": s12 / "test_per_class_metrics.csv",
        "primary_bootstrap_ci.csv": s12 / "block_bootstrap_ci.csv",
        "blocked_vs_random.csv": s13 / "blocked_vs_random_comparison.csv",
        "feature_ablation.csv": s14 / "feature_family_ablation.csv",
        "window_sensitivity.csv": s15 / "window_length_sensitivity.csv",
        "secondary_test_metrics.json": s16 / "test_metrics.json",
        "secondary_per_class.csv": s16 / "test_per_class_metrics.csv",
        "robustness_audit.json": s17 / "robustness_audit.json",
    }
    for name, source in source_tables.items():
        shutil.copy2(source, TABLES / name)

    required_checks = {
        "all_protected_locks_completed": all(lock_checks.values()),
        "primary_metrics_reproduce_from_predictions": all(primary_metric_checks.values()),
        "robustness_audit_pass": robustness.get("status") == "PASS",
        "window_650_reproduction_pass": load_json(s15 / "reproduction_audit_650.json").get("all_checks_pass") is True,
        "claim_C4_not_overstated": claim_evidence["C4"]["status"] == "Not supported",
        "claim_C5_not_overstated": claim_evidence["C5"]["status"] == "Not supported",
        "secondary_warning_present": "assembly" in secondary_metrics["mandatory_warning"].lower(),
    }
    audit = {
        "status": "PASS" if all(required_checks.values()) else "FAIL",
        "checks": required_checks,
        "lock_checks": lock_checks,
        "primary_metric_checks": primary_metric_checks,
    }
    (PACKAGE / "final_reconciliation_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")

    # Hash all authoritative inputs and final artifacts except this manifest itself.
    roots = [PROJECT / "05_data_manifest", PROJECT / "10_code", s12, s13, s14, s15, s16, s17, PACKAGE]
    paths = []
    for root in roots:
        paths.extend(path for path in root.rglob("*") if path.is_file() and path != MANIFEST and ".venv" not in path.parts)
    rows = [{
        "path": str(path.relative_to(PROJECT)),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    } for path in sorted(set(paths))]
    pd.DataFrame(rows).to_csv(MANIFEST, index=False)
    print(json.dumps(audit, indent=2))
    print(json.dumps(claim_evidence, indent=2))
    if audit["status"] != "PASS":
        raise SystemExit("Final result reconciliation failed")


if __name__ == "__main__":
    main()
