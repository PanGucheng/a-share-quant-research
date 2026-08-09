from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _is_ignored(path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--no-index", "--", path],
        cwd=PROJECT_ROOT,
        check=False,
    )
    assert result.returncode in {0, 1}
    return result.returncode == 0


@pytest.mark.parametrize(
    "path",
    [
        "outputs/new_experiment/result.csv",
        "outputs/factor_evaluation_v5/run/report.md",
        "tmp/cache/factor_frame.parquet",
        "data/forward/labels/example.csv",
        "logs/new_run.log",
        "outputs/forward/dry_run/2099-01-01/prediction.csv",
        "outputs/forward/metrics/metrics.json",
        "outputs/forward/unknown_runtime/session.bin",
        "outputs/forward/predictions/2099-01-01/debug_payload.json",
        "outputs/forward/predictions/2099-01-01/raw.csv",
        "outputs/forward/predictions/2099-01-01/features.csv",
        (
            "outputs/forward/predictions/2099-01-01/"
            "prediction_pending_receipt.json"
        ),
    ],
)
def test_runtime_paths_are_ignored(path: str) -> None:
    assert _is_ignored(path)


@pytest.mark.parametrize(
    "path",
    [
        "outputs/forward/predictions/2099-01-01/prediction.csv",
        "outputs/forward/predictions/2099-01-01/prediction_receipt.json",
        "outputs/forward/paper_portfolio/decisions/2099-01-01/decision.json",
        "outputs/forward/paper_portfolio/decisions/2099-01-01/target_weights.csv",
        "outputs/forward/status.json",
        "outputs/forward/paper_portfolio/status.json",
        "artifacts/example/sha256/model.bin",
        "reports/example_summary.md",
    ],
)
def test_durable_evidence_paths_are_trackable(path: str) -> None:
    assert not _is_ignored(path)
