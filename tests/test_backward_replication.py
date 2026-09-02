from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from factor_research.backward_replication import (
    Phase0Inputs,
    _validate_unique,
    aggregate_period_metrics,
    build_backward_portability,
    classify_backward_portability,
    compute_union_daily_ic,
    daily_rank_ic,
    enforce_label_maturity,
    load_phase0_config,
    preflight_phase0,
    reconcile_same_era,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "long_history_core_factor_phase0_v1.yaml"


@pytest.fixture(scope="module")
def verified_inputs():
    return preflight_phase0(load_phase0_config(CONFIG), root=ROOT)


def test_preflight_counts_and_no_factor_read(verified_inputs) -> None:
    assert len(verified_inputs.computation_universe) == 91
    assert verified_inputs.computation_universe["strategy_v1_member"].sum() == 52
    assert verified_inputs.computation_universe["mature_economic_member"].sum() == 39
    assert verified_inputs.computation_universe["factor"].is_unique
    strategy_rows = verified_inputs.inventory.loc[
        verified_inputs.inventory["old_source"].eq("strategy_v1")
    ]
    assert len(strategy_rows) == 52
    assert strategy_rows["old_direction"].isna().all()
    assert strategy_rows["direction_status"].eq("unsigned_membership").all()


def test_wrong_identity_fails_before_factor_read() -> None:
    config = copy.deepcopy(load_phase0_config(CONFIG))
    config["canonical_dataset_id"] = "canonical-dataset:wrong"
    called = False

    def probe() -> None:
        nonlocal called
        called = True

    with pytest.raises(ValueError, match="canonical manifest identity mismatch"):
        preflight_phase0(config, root=ROOT, factor_read_probe=probe)
    assert not called


@pytest.mark.parametrize(
    ("section", "expected_key", "message"),
    [
        ("strategy_v1", "expected_count", "Strategy V1 factor count drift"),
        ("economic", "expected_count", "mature economic factor count drift"),
    ],
)
def test_count_drift_fails(section: str, expected_key: str, message: str) -> None:
    config = copy.deepcopy(load_phase0_config(CONFIG))
    config[section][expected_key] += 1
    with pytest.raises(ValueError, match=message):
        preflight_phase0(config, root=ROOT)


def test_duplicate_daily_factor_date_fails_through_deduplicated_input() -> None:
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2020-01-02"] * 20),
            "factor_a": np.arange(20),
            "label_20d_t1": np.arange(20),
        }
    )
    result = daily_rank_ic(frame, ["factor_a"], min_count=20)
    assert len(result) == 1
    assert result.iloc[0]["raw_rank_ic"] == pytest.approx(1.0)


def test_duplicate_inventory_keys_fail() -> None:
    frame = pd.DataFrame(
        {
            "factor": ["x", "x"],
            "old_source": ["source", "source"],
            "old_context": ["context", "context"],
        }
    )
    with pytest.raises(ValueError, match="duplicate inventory keys"):
        _validate_unique(
            frame, ["factor", "old_source", "old_context"], "inventory"
        )


def test_metric_engine_rejects_duplicate_computation() -> None:
    inputs = Phase0Inputs(
        config={"computation": {"min_cross_section_count": 20}},
        inventory=pd.DataFrame(),
        computation_universe=pd.DataFrame({"factor": ["x"]}),
        partition_manifest=pd.DataFrame(),
        factor_lineage=pd.DataFrame(),
        source_hashes={},
    )
    with pytest.raises(ValueError, match="duplicate factors"):
        compute_union_daily_ic(
            inputs,
            pd.DataFrame(),
            root=ROOT,
            factors=["x", "x"],
        )


def test_one_factor_maps_to_multiple_old_contexts(verified_inputs) -> None:
    factor = "alpha158_CORD10"
    rows = verified_inputs.inventory.loc[
        verified_inputs.inventory["factor"].eq(factor)
        & verified_inputs.inventory["computation_included"]
    ]
    assert len(rows) > 1
    assert rows["old_context"].nunique() > 1


def test_early_opposite_ic_cannot_flip_frozen_direction() -> None:
    metrics = pd.DataFrame(
        {
            "period_id": [
                "early_2010_2014",
                "mid_2015_2018",
                "preexisting_2019_2020",
                "legacy_2021_2026",
            ],
            "frozen_direction_mean_rank_ic": [-0.02, 0.01, 0.02, 0.03],
        }
    )
    assert (
        classify_backward_portability(
            metrics, signed=True, reconciliation_comparable=True
        )
        == "recent_regime_concentrated"
    )


def test_period_boundaries_insufficient_history_and_unsigned() -> None:
    dates = pd.to_datetime(["2010-02-01", "2010-02-02", "2015-01-05"])
    daily = pd.DataFrame(
        {
            "datetime": dates,
            "factor": ["x"] * 3,
            "raw_rank_ic": [0.2, -0.1, 0.1],
            "pair_count": [30, 30, 30],
        }
    )
    universe = pd.DataFrame(
        {
            "factor": ["x"],
            "old_direction": [np.nan],
            "direction_status": ["unsigned_membership"],
        }
    )
    calendar = pd.DataFrame(
        {
            "period_id": ["early_2010_2014", "mid_2015_2018"],
            "requested_start": pd.to_datetime(["2010-01-29", "2015-01-01"]),
            "requested_end": pd.to_datetime(["2014-12-31", "2018-12-31"]),
            "actual_signal_start": pd.to_datetime(["2010-01-29", "2015-01-01"]),
            "actual_signal_end": pd.to_datetime(["2014-12-31", "2018-12-31"]),
            "eligible_date_count": [1000, 900],
            "label_maturity_cutoff": pd.to_datetime(["2026-05-11"] * 2),
        }
    )
    result = aggregate_period_metrics(daily, universe, calendar, min_valid_dates=3)
    assert result["coverage_status"].eq("insufficient_history").all()
    assert result["mean_raw_rank_ic"].isna().all()
    assert result["frozen_direction_mean_rank_ic"].isna().all()
    assert result.loc[result["period_id"].eq("early_2010_2014"), "actual_signal_end"].iloc[0] <= pd.Timestamp("2014-12-31")


def test_future_label_access_fails_and_effective_dates_are_enforced() -> None:
    calendar = pd.date_range("2020-01-01", periods=30, freq="B")
    labels = pd.DataFrame(
        {
            "datetime": [calendar[10]],
            "instrument": ["SH600000"],
            "label_20d_t1": [0.1],
            "label_exit_date": [calendar[-1] + pd.Timedelta(days=1)],
        }
    )
    with pytest.raises(ValueError, match="future-label access"):
        enforce_label_maturity(labels, calendar, as_of_date=calendar[-1], horizon=21)


def test_same_era_incompatible_is_not_comparable() -> None:
    daily = pd.DataFrame(
        columns=["datetime", "factor", "raw_rank_ic", "pair_count"]
    )
    universe = pd.DataFrame(
        {"factor": ["x"], "direction_status": ["signed"], "old_direction": [1]}
    )
    old = pd.DataFrame(
        {
            "outer_split_id": ["o"],
            "inner_split_id": ["i"],
            "factor": ["x"],
            "train_mean_ic": [0.1],
            "validation_mean_ic": [0.1],
        }
    )
    assignments = pd.DataFrame(
        {
            "outer_split_id": ["o"],
            "inner_split_id": ["i"],
            "datetime": ["2021-01-01"],
            "fold": ["train"],
        }
    )
    result = reconcile_same_era(
        daily,
        universe,
        old,
        assignments,
        consistent_tolerance=0.001,
        minor_tolerance=0.005,
        min_valid_dates=20,
    )
    assert set(result["same_era_reconciliation_status"]) == {"insufficient_history"}


def test_missing_old_factor_metric_is_explicit_but_allows_canonical_portability() -> None:
    daily = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2021-01-01"]),
            "factor": ["economic_x"],
            "raw_rank_ic": [0.1],
            "pair_count": [100],
        }
    )
    universe = pd.DataFrame(
        {
            "factor": ["economic_x"],
            "direction_status": ["signed"],
            "direction_authority": ["economic_predeclared"],
            "old_direction": [1],
            "mature_economic_member": [True],
        }
    )
    old = pd.DataFrame(
        columns=[
            "outer_split_id",
            "inner_split_id",
            "factor",
            "train_mean_ic",
            "validation_mean_ic",
        ]
    )
    assignments = pd.DataFrame(
        columns=["outer_split_id", "inner_split_id", "datetime", "fold"]
    )
    reconciliation = reconcile_same_era(
        daily,
        universe,
        old,
        assignments,
        consistent_tolerance=0.001,
        minor_tolerance=0.005,
        min_valid_dates=20,
    )
    assert reconciliation.iloc[0]["same_era_reconciliation_status"] == "not_comparable"
    assert reconciliation.iloc[0]["reconciliation_reason"] == "no_old_factor_level_metric"


def test_repeated_portability_build_is_deterministic() -> None:
    periods = [
        "early_2010_2014",
        "mid_2015_2018",
        "preexisting_2019_2020",
        "legacy_2021_2026",
    ]
    metrics = pd.DataFrame(
        {
            "factor": ["x"] * 4,
            "period_id": periods,
            "frozen_direction_mean_rank_ic": [0.01] * 4,
        }
    )
    universe = pd.DataFrame(
        {
            "factor": ["x"],
            "direction_status": ["signed"],
            "direction_authority": ["economic_predeclared"],
            "old_direction": [1],
        }
    )
    reconciliation = pd.DataFrame(
        {"factor": ["x"], "same_era_reconciliation_status": ["consistent"]}
    )
    first = build_backward_portability(metrics, universe, reconciliation)
    second = build_backward_portability(metrics, universe, reconciliation)
    pd.testing.assert_frame_equal(first, second)
