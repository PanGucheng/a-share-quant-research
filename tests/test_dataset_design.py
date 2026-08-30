from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from research_validation.dataset_design import (
    autocorrelations,
    classify_factor_history_layer,
    regime_window_coverage,
    theoretical_overlapping_return_ess,
)


def test_overlapping_return_ess_reflects_twenty_day_horizon() -> None:
    assert theoretical_overlapping_return_ess(40, 20) == pytest.approx(2.3988, rel=1e-3)
    assert theoretical_overlapping_return_ess(252, 20) == pytest.approx(12.9415, rel=1e-3)


def test_autocorrelation_detects_persistence() -> None:
    values = np.repeat(np.arange(20, dtype=float), 2)
    rho = autocorrelations(values, 3)
    assert rho[0] == 1.0
    assert rho[1] > rho[3] > 0


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ("$close,$amount,$vwap", "price_volume_core"),
        ("turnover_rate_f,$close", "daily_basic_plus_price_volume"),
        ("net_mf_amount,traded_amount_cny", "moneyflow_plus_price_volume"),
        ("information_available_date,revenue,total_mv_cny", "fundamental_pit_plus_daily_basic"),
    ],
)
def test_factor_history_layer_is_dependency_driven(fields: str, expected: str) -> None:
    assert classify_factor_history_layer(fields) == expected


def test_regime_coverage_uses_global_terciles_without_outcomes() -> None:
    dates = pd.bdate_range("2020-01-01", periods=90)
    descriptors = pd.DataFrame({"datetime": dates, "volatility": np.arange(90)})
    windows = pd.DataFrame(
        [{"window_id": "all", "start": dates[0], "end": dates[-1]}]
    )
    result = regime_window_coverage(descriptors, windows, ["volatility"])
    assert result.loc[0, "represented_terciles_min_5_dates"] == 3
    assert result.loc[0, ["low_dates", "middle_dates", "high_dates"]].sum() == 90


def test_final_manifest_preserves_governance_and_hashes() -> None:
    project_root = Path(__file__).resolve().parents[1]
    output_dir = project_root / "reports" / "historical_dataset_validation_design_v1"
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["artifact_status"] == "research_complete"
    assert manifest["formal_structured_ml_competition_started"] is False
    assert manifest["dataset_window_selected_from_model_outcomes"] is False
    assert manifest["structured_ml_outcomes_read"] is False
    assert manifest["research_protocol_v2_changed"] is False
    assert manifest["frozen_matrix_changed"] is False
    assert manifest["strategy_v1_changed"] is False
    assert manifest["forward_track_changed"] is False
    assert manifest["authoritative_raw_snapshots_changed"] is False
    assert manifest["network_probe_receipts_present"] is True

    for name, expected_hash in manifest["output_file_hashes"].items():
        actual_hash = hashlib.sha256((output_dir / name).read_bytes()).hexdigest()
        assert actual_hash == expected_hash
