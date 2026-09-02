from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from research_validation.feature_matrix import canonical_hash, file_sha256

from .execution_profiles import with_lightgbm_threads
from .lightgbm_models import load_lightgbm_config
from .thread_determinism import AUDIT_STAGE_ID


def load_full_execution_profile(path: Path) -> dict[str, Any]:
    profile = yaml.safe_load(path.read_text(encoding="utf-8"))
    if profile.get("profile_id") != "full_research_exact_mt_v2":
        raise ValueError("unexpected Full execution profile")
    if profile.get("reference_profile") != "full_research_v1_1t":
        raise ValueError("Full MT reference profile changed")
    if profile.get("parity_requirement") != "exact":
        raise ValueError("Full MT must require exact parity")
    if profile.get("authoritative_execution") is not True:
        raise ValueError("Full exact MT profile authority flag changed")
    if profile.get("scientific_model_selection_authorized") is not False:
        raise ValueError("Full execution profile cannot select scientific models")
    if profile.get("strategy_v2_authorized") is not False:
        raise ValueError("Full execution profile cannot authorize Strategy V2")
    if int(profile.get("num_threads", 0)) < 2:
        raise ValueError("Full MT profile requires multiple threads")
    return profile


def _load_verified_summary(path: Path) -> dict[str, Any]:
    summary = json.loads(path.read_text(encoding="utf-8"))
    recorded_summary_hash = summary.pop("summary_sha256", None)
    if recorded_summary_hash != canonical_hash(summary):
        raise ValueError("thread qualification summary hash is invalid")
    summary["summary_sha256"] = recorded_summary_hash
    if summary.get("stage_id") != AUDIT_STAGE_ID:
        raise ValueError("execution profile requires thread determinism audit evidence")
    required_outputs = {
        "runs.csv",
        "candidate_metrics.csv",
        "parity.csv",
        "thread_scaling.csv",
        "runtime_timing.csv",
        "access_audit.csv",
        "input_identity.json",
    }
    if set(summary.get("output_sha256", {})) != required_outputs:
        raise ValueError("thread qualification output inventory is incomplete")
    for name, expected_hash in summary["output_sha256"].items():
        output = path.parent / name
        if not output.is_file() or file_sha256(output) != expected_hash:
            raise ValueError(f"thread qualification output is missing or changed: {name}")
    identities = json.loads((path.parent / "input_identity.json").read_text(encoding="utf-8"))
    if not identities or not all(
        row.get("input_variables_constant_across_threads") is True for row in identities
    ):
        raise ValueError("thread qualification input identity is incomplete")
    return summary


def _assert_parity_scope(
    *,
    summary_path: Path,
    expected_workloads: set[str],
    num_threads: int,
    candidates_per_workload: int,
    parity_field: str,
) -> None:
    import pandas as pd

    metrics = pd.read_csv(summary_path.parent / "candidate_metrics.csv")
    parity = pd.read_csv(summary_path.parent / "parity.csv")
    if set(metrics["workload_id"].astype(str)) != expected_workloads:
        raise ValueError("thread qualification workload scope is incomplete")
    if set(parity["workload_id"].astype(str)) != expected_workloads:
        raise ValueError("thread qualification parity scope is incomplete")
    if set(metrics["thread_count"].astype(int)) != {1, 2, 4, 8}:
        raise ValueError("thread qualification thread coverage is incomplete")
    if set(metrics["repeat"].astype(int)) != {0, 1}:
        raise ValueError("thread qualification repeat coverage is incomplete")
    for workload_id in expected_workloads:
        for thread_count in sorted(metrics["thread_count"].astype(int).unique()):
            for repeat in sorted(metrics["repeat"].astype(int).unique()):
                rows = metrics.loc[
                    metrics["workload_id"].eq(workload_id)
                    & metrics["thread_count"].eq(thread_count)
                    & metrics["repeat"].eq(repeat)
                ]
                if (
                    len(rows) != candidates_per_workload
                    or rows["candidate_sha256"].nunique() != candidates_per_workload
                ):
                    raise ValueError("thread qualification candidate coverage is incomplete")
    required = parity.loc[
        parity["thread_count"].eq(int(num_threads))
        & parity["workload_id"].isin(expected_workloads)
        & parity["comparison_kind"].isin(["cross_thread", "same_thread_repeat"])
    ]
    expected_rows = len(expected_workloads) * candidates_per_workload * 2
    if len(required) != expected_rows or not required[parity_field].eq(True).all():
        raise ValueError(f"requested thread count failed {parity_field}")


def qualified_fast_execution_summary(
    *, qualification_summary_path: Path, num_threads: int
) -> dict[str, Any]:
    summary = _load_verified_summary(qualification_summary_path)
    if summary.get("fast_mt_qualification_scope") is not True:
        raise ValueError("thread audit did not cover the Fast MT qualification scope")
    if int(num_threads) not in [
        int(value) for value in summary["scientifically_equivalent_thread_counts"]
    ]:
        raise ValueError("requested Fast thread count lacks scientific parity")
    if summary.get("same_thread_repeats_exact") is not True:
        raise ValueError("Fast MT requires exact same-thread repeats")
    expected = {
        f"{split_id}__{policy_id}"
        for split_id in ("split_001", "split_002")
        for policy_id in (
            "strict_current_baseline",
            "current_plus_existing_conditional_signal",
            "broad_data_qualified",
        )
    }
    _assert_parity_scope(
        summary_path=qualification_summary_path,
        expected_workloads=expected,
        num_threads=num_threads,
        candidates_per_workload=4,
        parity_field="scientific_parity",
    )
    return summary


def qualified_full_execution_config(
    *,
    frozen_config_path: Path,
    qualification_summary_path: Path,
    num_threads: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a Full MT config only from intact exact-parity qualification evidence."""
    frozen = load_lightgbm_config(frozen_config_path)
    summary = _load_verified_summary(qualification_summary_path)
    if summary.get("full_authoritative_qualification_scope") is not True:
        raise ValueError("thread audit did not cover the Full qualification scope")
    if summary.get("full_authoritative_eligible") is not True:
        raise ValueError("thread audit did not qualify Full MT")
    if summary.get("same_thread_repeats_exact") is not True:
        raise ValueError("Full MT requires exact same-thread repeats")
    if int(num_threads) not in [int(value) for value in summary["exact_thread_counts"]]:
        raise ValueError("requested Full thread count lacks exact parity")
    if summary.get("frozen_lightgbm_config_sha256") != canonical_hash(frozen):
        raise ValueError("qualification evidence belongs to another frozen config")
    expected = {
        f"split_001__{policy_id}"
        for policy_id in (
            "strict_current_baseline",
            "current_plus_existing_conditional_signal",
            "broad_data_qualified",
        )
    }
    _assert_parity_scope(
        summary_path=qualification_summary_path,
        expected_workloads=expected,
        num_threads=num_threads,
        candidates_per_workload=16,
        parity_field="exact_parity",
    )
    execution = with_lightgbm_threads(frozen, int(num_threads))
    execution["execution_profile"] = "full_research_exact_mt_v2"
    execution["qualification_summary_sha256"] = summary["summary_sha256"]
    execution["reference_profile"] = "full_research_v1_1t"
    return execution, summary


def qualified_full_execution_profile(
    profile_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from .protocol import resolve

    profile = load_full_execution_profile(profile_path)
    config, summary = qualified_full_execution_config(
        frozen_config_path=resolve(profile["reference_config"]),
        qualification_summary_path=resolve(profile["qualification_summary"]),
        num_threads=int(profile["num_threads"]),
    )
    if summary["summary_sha256"] != profile["qualification_summary_sha256"]:
        raise ValueError("Full execution profile qualification hash changed")
    return config, summary
