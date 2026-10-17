from __future__ import annotations

import ast
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / "10_code" / "train_benchmark.py"
CONFIG = PROJECT / "05_data_manifest" / "frozen_training_isolation.json"
OUTPUT = PROJECT / "05_data_manifest" / "training_isolation_audit.json"


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(text)
    json.loads(CONFIG.read_text(encoding="utf-8"))

    evaluate = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "evaluate"
    )
    evaluate_text = ast.get_source_segment(text, evaluate) or ""
    checks = {
        "candidate_fit_uses_training_only": 'model.fit(X["train"], y["train"])' in evaluate_text,
        "validation_prediction_used_for_ranking": 'model.predict(X["validation"])' in evaluate_text,
        "test_metric_not_in_sort_keys": '"test_macro_f1"' not in evaluate_text.split("sort_values", 1)[1].split(")", 1)[0],
        "fresh_clone_for_final_model": "final_model = clone(" in evaluate_text,
        "final_refit_uses_development_partition": 'final_model.fit(development[feature_cols], development["label"])' in evaluate_text,
        "single_literal_test_prediction_call": evaluate_text.count('predict(X["test"])') == 1,
        "imputer_is_pipeline_step": '("imputer", SimpleImputer(strategy="median"))' in text,
        "scaler_is_pipeline_step": '("scaler", StandardScaler())' in text,
        "no_smote_or_resampling": "SMOTE" not in text and "RandomOverSampler" not in text and "RandomUnderSampler" not in text,
    }
    audit = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "source": str(SOURCE),
        "configuration": str(CONFIG),
        "checks": checks,
        "important_scope_note": "This static audit verifies the confirmatory evaluate() path. Step 12 must additionally log the selected feature set before the one permitted test prediction."
    }
    OUTPUT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))
    if audit["status"] != "PASS":
        raise SystemExit("Training/test isolation audit failed")


if __name__ == "__main__":
    main()
