from __future__ import annotations

import json
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
    file_sha256,
    load_phase0_config,
    preflight_phase0,
    reconcile_same_era,
)
from research_validation.canonical_dataset import (
    canonical_dataset_identity,
    canonical_hash,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "long_history_core_factor_phase0_v1.yaml"


@pytest.fixture(scope="module")
def verified_inputs():
    canonical_manifest = ROOT / "outputs/canonical_historical_dataset_assembly_v1/current/manifest.json"
    if not canonical_manifest.is_file():
        pytest.skip("local frozen Phase 0 parent evidence is not tracked in Git")
    return preflight_phase0(load_phase0_config(CONFIG), root=ROOT)


def _write_phase0_fixture(root: Path) -> dict:
    def write_json(name: str, payload: dict) -> Path:
        path = root / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def write_csv(name: str, rows: list[dict]) -> Path:
        path = root / name
        pd.DataFrame(rows).to_csv(path, index=False)
        return path

    partition_manifest = pd.DataFrame(
        [
            {
                "segment_id": "segment",
                "partition_id": "partition",
                "effective_start": "2020-01-01",
                "effective_end": "2020-12-31",
                "output_sha256": "fixture",
                "row_count": 1,
                "factor_count": 2,
                "lineage_action": "fixture",
                "factors": "economic_x,strategy_x",
            }
        ]
    )
    factor_lineage = pd.DataFrame(
        [
            {
                "factor": factor,
                "authoritative_semantics": "fixture",
                "historical_action": "fixture",
                "continuation_action": "fixture",
                "research_usable": True,
            }
            for factor in ["economic_x", "strategy_x"]
        ]
    )
    partition_path = root / "partition_manifest.csv"
    lineage_path = root / "factor_lineage.csv"
    partition_manifest.to_csv(partition_path, index=False)
    factor_lineage.to_csv(lineage_path, index=False)
    identity = canonical_dataset_identity(partition_manifest, factor_lineage)
    manifest_path = write_json("canonical_manifest.json", {"canonical_dataset_id": identity})

    features = ["strategy_x"]
    feature_hash = canonical_hash(features)
    preprocessing_path = write_json("preprocessing.json", {"feature_names": features})
    freeze_path = write_json(
        "freeze.json", {"factor_count": 1, "feature_order_sha256": feature_hash}
    )
    economic_map_path = write_csv(
        "economic_map.csv",
        [
            {
                "factor": "economic_x",
                "research_role": "selected_sleeve_member",
                "sleeve_id": "fixture_sleeve",
                "expected_direction": 1,
                "mechanism": "fixture",
            }
        ],
    )
    economic_manifest_path = write_json("economic_manifest.json", {"fixture": True})
    literature_path = write_csv("literature.csv", [{"fixture": True}])
    board_path = write_csv(
        "board.csv",
        [
            {
                "outer_split_id": "outer",
                "factor": "strategy_x",
                "frozen_direction": -1,
                "stability_role": "fixture",
            }
        ],
    )
    history_row = {
        "outer_split_id": "outer",
        "inner_split_id": "inner",
        "factor": "strategy_x",
        "frozen_direction": -1,
    }
    direction_path = write_csv("direction.csv", [history_row])
    window_path = write_csv("window.csv", [history_row])
    selection_path = write_csv(
        "selection.csv", [{**history_row, "selected": True, "selection_reason": "fixture"}]
    )
    resolved_path = write_json("resolved.json", {"fixture": True})
    assignments_path = write_csv("assignments.csv", [{"fixture": True}])
    representatives_path = write_csv(
        "representatives.csv",
        [
            {
                "outer_split_id": "outer",
                "cluster_id": "cluster",
                "factor": "strategy_x",
                "is_representative": True,
            }
        ],
    )
    memberships_path = write_csv(
        "memberships.csv",
        [{"outer_split_id": "outer", "factor": "strategy_x", "cluster_id": "cluster"}],
    )

    def source(path: Path) -> dict[str, str]:
        return {"path": str(path), "sha256": file_sha256(path)}

    fixture_sources = {
        "freeze": source(freeze_path),
        "preprocessing": source(preprocessing_path),
        "economic_map": source(economic_map_path),
        "economic_manifest": source(economic_manifest_path),
        "literature": source(literature_path),
        "board": source(board_path),
        "direction": source(direction_path),
        "window": source(window_path),
        "selection": source(selection_path),
        "resolved": source(resolved_path),
        "assignments": source(assignments_path),
        "representatives": source(representatives_path),
        "memberships": source(memberships_path),
    }
    return {
        "canonical_dataset_id": identity,
        "canonical_manifest": str(manifest_path),
        "partition_manifest": str(partition_path),
        "factor_lineage": str(lineage_path),
        "strategy_v1": {
            "freeze": fixture_sources["freeze"]["path"],
            "freeze_sha256": fixture_sources["freeze"]["sha256"],
            "preprocessing": fixture_sources["preprocessing"]["path"],
            "preprocessing_sha256": fixture_sources["preprocessing"]["sha256"],
            "expected_count": 1,
            "expected_feature_order_sha256": feature_hash,
        },
        "economic": {
            "map": fixture_sources["economic_map"]["path"],
            "map_sha256": fixture_sources["economic_map"]["sha256"],
            "manifest": fixture_sources["economic_manifest"]["path"],
            "manifest_sha256": fixture_sources["economic_manifest"]["sha256"],
            "literature_map": fixture_sources["literature"]["path"],
            "literature_map_sha256": fixture_sources["literature"]["sha256"],
            "expected_count": 1,
            "membership_filter": "selected_sleeve_member",
        },
        "stability": {
            "board": fixture_sources["board"]["path"],
            "board_sha256": fixture_sources["board"]["sha256"],
            "direction_history": fixture_sources["direction"]["path"],
            "direction_history_sha256": fixture_sources["direction"]["sha256"],
            "window_metrics": fixture_sources["window"]["path"],
            "window_metrics_sha256": fixture_sources["window"]["sha256"],
            "selection_history": fixture_sources["selection"]["path"],
            "selection_history_sha256": fixture_sources["selection"]["sha256"],
            "resolved_config": fixture_sources["resolved"]["path"],
            "resolved_config_sha256": fixture_sources["resolved"]["sha256"],
            "date_assignments": fixture_sources["assignments"]["path"],
            "date_assignments_sha256": fixture_sources["assignments"]["sha256"],
        },
        "clustering": {
            "representatives": fixture_sources["representatives"]["path"],
            "representatives_sha256": fixture_sources["representatives"]["sha256"],
            "memberships": fixture_sources["memberships"]["path"],
            "memberships_sha256": fixture_sources["memberships"]["sha256"],
        },
        "computation": {
            "expected_unique_count": 2,
            "expected_union_sha256": canonical_hash(["economic_x", "strategy_x"]),
            "explicit_extras": [],
        },
    }


def test_synthetic_preflight_is_self_contained(tmp_path: Path) -> None:
    inputs = preflight_phase0(_write_phase0_fixture(tmp_path), root=ROOT)
    assert inputs.computation_universe["factor"].tolist() == [
        "economic_x",
        "strategy_x",
    ]
    strategy = inputs.computation_universe.set_index("factor").loc["strategy_x"]
    assert strategy["direction_authority"] == "inherited_from_rolling_stability"
    assert inputs.inventory["computation_included"].all()


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


def test_wrong_identity_fails_before_factor_read(tmp_path: Path) -> None:
    config = _write_phase0_fixture(tmp_path)
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
def test_count_drift_fails(
    tmp_path: Path, section: str, expected_key: str, message: str
) -> None:
    config = _write_phase0_fixture(tmp_path)
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
