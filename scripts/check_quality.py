from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RUFF_TARGETS = (
    "qlib_baseline",
    "daily_update",
    "scripts/check_quality.py",
    "scripts/daily_update.py",
    "scripts/run_forward_prediction_v1.py",
    "scripts/update_forward_labels_v1.py",
    "scripts/show_forward_status_v1.py",
    "scripts/run_paper_portfolio_v1.py",
)

FAST_TESTS = (
    "tests/test_project_settings.py",
    "tests/test_project_doctor.py",
    "tests/test_project_io.py",
    "tests/test_weak_cache.py",
    "tests/test_active_cli.py",
    "tests/test_imports.py",
    "tests/test_ci_policy.py",
    "tests/test_quality_commands.py",
)

SYNTHETIC_VALIDATORS = (
    "scripts/validate_research_data_contracts_v1.py",
    "scripts/validate_point_in_time_universe_v1.py",
    "scripts/validate_point_in_time_universe_v2.py",
    "scripts/validate_purged_walk_forward_v1.py",
    "scripts/validate_factor_multiple_testing_v1.py",
    "scripts/validate_factor_rolling_stability_v1.py",
    "scripts/validate_factor_clustering_v1.py",
    "scripts/validate_factor_score_construction_v1.py",
    "scripts/validate_a_share_execution_v1.py",
    "scripts/validate_external_exposure_data_v1.py",
    "scripts/validate_final_portfolio_diagnostics_v1.py",
    "scripts/validate_reference_pipeline_consistency_v1.py",
    "scripts/validate_execution_reconciliation_v1.py",
    "scripts/validate_qlib_exchange_v1.py",
    "scripts/validate_full_research_trial_v1.py",
    "scripts/validate_full_research_669_v1.py",
    "scripts/validate_factor_universe_v2_matrix_closeout.py",
    "scripts/validate_selection_integrity_receipts_v1.py",
    "scripts/validate_accuracy_correction_hard_stop_v1.py",
    "scripts/validate_data_source_audit_v2.py",
    "scripts/validate_execution_unit_semantics_v1_2.py",
    "scripts/validate_historical_instrument_state_canary_v2.py",
    "scripts/validate_research_model_protocol_v1.py",
    "scripts/validate_research_model_protocol_v1_1.py",
    "scripts/validate_prospective_forward_candidate_v1.py",
    "scripts/validate_prospective_forward_hardening_v1.py",
)

QLIB_RUNTIME_TESTS = ("tests/test_qlib_exchange_runtime.py",)


def commands_for_tier(tier: str) -> tuple[tuple[str, ...], ...]:
    python = sys.executable
    if tier == "fast":
        return (
            (python, "-m", "ruff", "check", *RUFF_TARGETS),
            (python, "-m", "pytest", "-q", *FAST_TESTS),
        )
    if tier == "full":
        return (
            (python, "-m", "pytest", "-q"),
            *((python, validator) for validator in SYNTHETIC_VALIDATORS),
        )
    if tier == "qlib":
        return ((python, "-m", "pytest", "-q", *QLIB_RUNTIME_TESTS),)
    raise ValueError(f"Unknown quality tier: {tier}")


def run_commands(
    commands: Sequence[Sequence[str]],
    *,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> int:
    for command in commands:
        print(f"+ {subprocess.list2cmdline(list(command))}", flush=True)
        result = runner(list(command), cwd=PROJECT_ROOT, check=False)
        if result.returncode:
            return int(result.returncode)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a local/CI quality tier.")
    parser.add_argument("tier", choices=("fast", "full", "qlib"))
    args = parser.parse_args()
    return run_commands(commands_for_tier(args.tier))


if __name__ == "__main__":
    raise SystemExit(main())
