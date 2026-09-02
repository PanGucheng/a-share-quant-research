from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from research_validation.feature_matrix import canonical_hash, file_sha256

from model_research.execution_profiles import with_lightgbm_threads
from model_research.fast_research import load_fast_research_config
from model_research.full_execution import (
    load_full_execution_profile,
    qualified_full_execution_config,
)
from model_research.resource_scheduler import (
    ResourceBudget,
    WorkloadClass,
    candidate_worker_thread_plans,
)
from model_research.thread_determinism import (
    _candidate_order,
    _first_divergence,
    _leaf_difference,
    load_thread_audit_config,
)


def test_execution_thread_override_does_not_mutate_frozen_config() -> None:
    frozen = {
        "determinism": {"num_threads": 1, "seed": 7},
        "resources": {"threads": 1},
    }
    overridden = with_lightgbm_threads(frozen, 8)
    assert frozen["determinism"]["num_threads"] == 1
    assert frozen["resources"]["threads"] == 1
    assert overridden["determinism"]["num_threads"] == 8
    assert overridden["resources"]["threads"] == 8


def test_real_audit_and_fast_mt_profiles_are_non_authoritative() -> None:
    audit = load_thread_audit_config(
        Path("configs/lightgbm_thread_determinism_audit_v1.yaml")
    )
    assert audit["thread_counts"] == [1, 2, 4, 8]
    assert {row["policy_id"] for row in audit["workloads"]} == {
        "strict_current_baseline",
        "current_plus_existing_conditional_signal",
        "broad_data_qualified",
    }
    fast = load_fast_research_config(Path("configs/fast_research_mt_v2.yaml"))
    assert fast["profile_id"] == "fast_research_mt_v2"
    assert fast["num_threads"] == 8
    assert fast["authoritative_execution"] is False
    assert fast["single_thread_fallback"]["enabled"] is True
    fast_audit = load_thread_audit_config(
        Path("configs/lightgbm_thread_determinism_fast_mt_qualification_v1.yaml")
    )
    assert fast_audit["fast_mt_qualification"] is True
    assert len(fast_audit["workloads"]) == 6
    full = load_full_execution_profile(
        Path("configs/research_lightgbm_full_exact_mt_v2.yaml")
    )
    assert full["num_threads"] == 8
    assert full["parity_requirement"] == "exact"


def test_tree_leaf_comparison_and_divergence_classification() -> None:
    assert _leaf_difference({"0:L": 1.0}, {"0:L": 1.0}) == {
        "leaf_paths_identical": True,
        "leaf_value_max_abs_difference": 0.0,
        "leaf_value_mean_abs_difference": 0.0,
    }
    changed = _leaf_difference({"0:L": 1.0}, {"0:L": 1.0001})
    assert changed["leaf_value_max_abs_difference"] > 0
    row = {
        "tree_topology_identical": True,
        "leaf_values_exact": False,
        "prediction_exact": False,
        "daily_rank_ic_exact": False,
        "candidate_ordering_identical": True,
        "selected_candidate_identical": True,
    }
    assert _first_divergence(row) == "leaf_values"


def test_candidate_order_is_stable_and_uses_frozen_tie_breaks() -> None:
    rows = pd.DataFrame(
        [
            {
                "candidate_sha256": "complex",
                "mean_daily_rank_ic": 0.1,
                "daily_rank_ic_ir": 1.0,
                "prediction_coverage": 1.0,
                "num_leaves": 31,
                "max_depth": 6,
                "num_boost_round": 200,
            },
            {
                "candidate_sha256": "simple",
                "mean_daily_rank_ic": 0.1,
                "daily_rank_ic_ir": 1.0,
                "prediction_coverage": 1.0,
                "num_leaves": 15,
                "max_depth": 4,
                "num_boost_round": 100,
            },
        ]
    )
    assert _candidate_order(rows) == ["simple", "complex"]


def test_resource_plans_never_oversubscribe_cpu_or_ram() -> None:
    plans = candidate_worker_thread_plans(
        ResourceBudget(
            physical_cores=8,
            logical_cores=16,
            available_ram_mib=32_000,
            reserved_ram_mib=4_000,
        ),
        WorkloadClass("broad", peak_rss_mib_per_worker=17_000),
    )
    assert plans
    assert all(row.cpu_budget_valid and row.ram_budget_valid for row in plans)
    assert all(row.workers == 1 for row in plans)


def test_full_mt_runner_rejects_nonqualifying_evidence(tmp_path: Path) -> None:
    identity_path = tmp_path / "input_identity.json"
    identity_path.write_text(
        json.dumps([{"input_variables_constant_across_threads": True}]),
        encoding="utf-8",
    )
    summary = {
        "stage_id": "lightgbm_thread_determinism_audit_v1",
        "full_authoritative_qualification_scope": False,
        "full_authoritative_eligible": False,
        "same_thread_repeats_exact": True,
        "exact_thread_counts": [1, 2],
        "frozen_lightgbm_config_sha256": "not-used",
        "output_sha256": {
            "input_identity.json": file_sha256(identity_path),
        },
    }
    summary["summary_sha256"] = canonical_hash(summary)
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(ValueError, match="inventory"):
        qualified_full_execution_config(
            frozen_config_path=Path("configs/research_lightgbm_v1.yaml"),
            qualification_summary_path=path,
            num_threads=2,
        )
