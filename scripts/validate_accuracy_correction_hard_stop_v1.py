from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.model_entry_gate import (  # noqa: E402
    ModelEntryBlockedError,
    assert_model_entry_files,
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    config = yaml.safe_load(
        resolve("configs/accuracy_correction_v1.yaml").read_text(encoding="utf-8")
    )
    assert config["status"] == "active"

    readiness = pd.read_csv(resolve(config["readiness_summary"]))
    assert len(readiness) == 1
    flags = readiness.iloc[0]
    assert bool(flags["selection_holdout_integrity_ready"])
    assert bool(flags["universe_lifecycle_v2_ready"])
    assert bool(flags["factor_dependency_inventory_ready"])
    assert bool(flags["matrix_v4_canary_ready"])
    assert bool(flags["matrix_v4_lifecycle_clean"])
    assert bool(flags["labels_v2_ready"])
    assert bool(flags["pairwise_ic_ready"])
    assert bool(flags["bootstrap_gap_policy_ready"])
    assert bool(flags["corrected_outer_fdr_ready"])
    assert bool(flags["corrected_stability_ready"])
    assert bool(flags["corrected_clustering_ready"])
    assert bool(flags["corrected_allowlist_ready"])
    for field in [
        "research_formula_accuracy_ready",
        "model_research_ready",
        "execution_semantics_accuracy_ready",
        "market_cache_v2_ready",
        "stale_policy_valid",
        "authoritative_oos_execution_ready",
        "core_model_ready",
        "pr5_model_training_ready",
        "model_training_started",
        "unbiased_final_estimate",
    ]:
        assert not bool(flags[field]), field
    assert int(flags["future_market_field_count"]) > 0
    assert bool(flags["model_entry_hard_stop_active"])
    assert bool(flags["historical_test_already_observed"])
    assert flags["selection_integrity_status"] == "ready"
    assert (
        flags["accuracy_correction_status"]
        == "blocked_research_and_execution_accuracy"
    )

    selections = pd.read_csv(resolve(config["selection_status"]))
    assert not selections["model_input_allowed"].astype(bool).any()
    current = selections.loc[
        selections["selection_name"].eq(
            "split_specific_holdout_clean_allowlists_v1"
        )
    ].iloc[0]
    assert current["selection_status"] == "superseded_accuracy_correction"
    assert current["superseded_by"] == "pending_matrix_v4_split_allowlists"

    supersession = pd.read_csv(resolve(config["artifact_supersession"]))
    assert {
        "universe",
        "matrix",
        "labels",
        "daily_ic",
        "fdr",
        "stability",
        "clustering",
        "allowlist",
        "weights",
        "freeze",
        "score",
        "execution",
        "historical_oos_nav",
    } == set(supersession["artifact_type"])
    assert not supersession["model_input_allowed"].astype(bool).any()
    assert not supersession["authoritative_evidence"].astype(bool).any()
    assert supersession.loc[
        supersession["artifact_type"].isin(["execution", "historical_oos_nav"]),
        "status",
    ].eq("non_authoritative").all()

    contracts = pd.read_csv(resolve(config["contract_status"]))
    assert contracts["status"].eq("pass").all()
    assert contracts["severity"].eq("critical").all()

    try:
        assert_model_entry_files(
            resolve(
                "outputs/full_research_669_readiness_v1/current/"
                "readiness_summary.csv"
            ),
            resolve(config["selection_status"]),
            selection_name="split_specific_holdout_clean_allowlists_v1",
            accuracy_correction_path=resolve(config["readiness_summary"]),
        )
    except ModelEntryBlockedError as exc:
        assert "accuracy_correction_status" in str(exc)
    else:
        raise AssertionError("active Accuracy Correction hard-stop did not block model entry")

    print(
        "Accuracy Correction V1 hard-stop is active; all current model inputs "
        "and historical OOS evidence are superseded or non-authoritative."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
