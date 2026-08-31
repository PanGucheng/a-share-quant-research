from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.check_quality import (
    FAST_TESTS,
    QLIB_RUNTIME_TESTS,
    RUFF_TARGETS,
    SYNTHETIC_VALIDATORS,
    commands_for_tier,
    run_commands,
)


def test_fast_tier_has_finite_ruff_scope_and_foundation_tests() -> None:
    commands = commands_for_tier("fast")
    assert commands[0] == (sys.executable, "-m", "ruff", "check", *RUFF_TARGETS)
    assert commands[1] == (sys.executable, "-m", "pytest", "-q", *FAST_TESTS)
    assert set(RUFF_TARGETS) == {
        "qlib_baseline",
        "daily_update",
        "scripts/check_quality.py",
        "scripts/daily_update.py",
        "scripts/run_forward_prediction_v1.py",
        "scripts/update_forward_labels_v1.py",
        "scripts/show_forward_status_v1.py",
        "scripts/run_paper_portfolio_v1.py",
    }
    assert not any(
        target in RUFF_TARGETS for target in (".", "factor_research", "model_research")
    )
    assert "tests/test_project_settings.py" in FAST_TESTS
    assert "tests/test_weak_cache.py" in FAST_TESTS
    assert "tests/test_active_cli.py" in FAST_TESTS


def test_full_tier_reuses_pytest_and_existing_validators() -> None:
    commands = commands_for_tier("full")
    assert commands[0] == (sys.executable, "-m", "pytest", "-q")
    assert tuple(command[1] for command in commands[1:]) == SYNTHETIC_VALIDATORS
    assert len(SYNTHETIC_VALIDATORS) == 26
    assert "scripts/validate_factor_universe_v2_matrix_closeout.py" in SYNTHETIC_VALIDATORS
    assert all(
        Path(validator).name.startswith("validate_")
        for validator in SYNTHETIC_VALIDATORS
    )
    assert not any(
        "train" in validator or "backtest" in validator
        for validator in SYNTHETIC_VALIDATORS
    )


def test_every_legacy_frozen_contract_keeps_its_closeout_validator() -> None:
    registry = json.loads(
        Path("configs/legacy_frozen_manifest_contracts_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert registry["artifacts"]
    assert all(
        contract["closeout_validator"] in SYNTHETIC_VALIDATORS
        for contract in registry["artifacts"]
    )


def test_qlib_tier_only_runs_synthetic_exchange_runtime_test() -> None:
    assert QLIB_RUNTIME_TESTS == ("tests/test_qlib_exchange_runtime.py",)
    assert commands_for_tier("qlib") == (
        (sys.executable, "-m", "pytest", "-q", *QLIB_RUNTIME_TESTS),
    )


def test_quality_runner_stops_on_first_failure() -> None:
    calls: list[tuple[list[str], Path, bool]] = []

    def runner(
        command: list[str], *, cwd: Path, check: bool
    ) -> subprocess.CompletedProcess:
        calls.append((command, cwd, check))
        return subprocess.CompletedProcess(command, 7)

    result = run_commands(
        (("python", "first.py"), ("python", "second.py")), runner=runner
    )

    assert result == 7
    assert [call[0] for call in calls] == [["python", "first.py"]]
    assert calls[0][2] is False


def test_workflow_uses_unified_quality_tiers() -> None:
    workflow = Path(".github/workflows/research-validation-ci.yml").read_text(
        encoding="utf-8"
    )
    assert "python scripts/check_quality.py fast" in workflow
    assert "python scripts/check_quality.py full" in workflow
    assert "python scripts/check_quality.py qlib" in workflow
    assert "python -m pytest -q" not in workflow
