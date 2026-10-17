from __future__ import annotations

import importlib.util
import itertools
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT / "05_data_manifest" / "frozen_classifier_search.json"
OUTPUT_PATH = PROJECT / "05_data_manifest" / "classifier_search_audit.json"
TRAIN_PATH = PROJECT / "10_code" / "train_benchmark.py"


def grid_count(grid: dict) -> int:
    if not grid:
        return 1
    return len(list(itertools.product(*grid.values())))


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location("train_benchmark", TRAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    code_candidates = module.candidates()

    declared = config["models"]
    names_match = list(code_candidates) == list(declared)
    per_model = {}
    for name, details in declared.items():
        calculated = grid_count(details["grid"])
        coded = len(code_candidates.get(name, []))
        per_model[name] = {
            "declared": details["candidate_count"],
            "calculated_from_grid": calculated,
            "instantiated_by_code": coded,
            "pass": details["candidate_count"] == calculated == coded,
        }

    per_set = sum(item["declared"] for item in per_model.values())
    expected_total = per_set * len(config["feature_sets"])
    status = (
        names_match
        and all(item["pass"] for item in per_model.values())
        and per_set == config["candidate_budget_per_feature_set"]
        and expected_total == config["total_candidate_budget_primary_split"]
    )
    audit = {
        "status": "PASS" if status else "FAIL",
        "config": str(CONFIG_PATH),
        "model_order_matches_code": names_match,
        "classifier_families_including_dummy": len(declared),
        "real_classifier_families": len(declared) - 1,
        "feature_sets": len(config["feature_sets"]),
        "candidates_per_feature_set": per_set,
        "total_primary_candidates": expected_total,
        "per_model": per_model,
    }
    OUTPUT_PATH.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))
    if not status:
        raise SystemExit("Frozen classifier audit failed")


if __name__ == "__main__":
    main()
