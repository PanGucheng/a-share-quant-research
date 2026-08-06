from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import qlib_integration.historical_portfolio_backtest as backtest
from qlib_integration.exchange_adapter import TPlusOneLedger, component_costs
from qlib_integration.strategy_adapter import (
    PeriodicEqualWeightSelector,
    equal_weight_targets,
    rebalance_execution_dates,
)
from research_validation.feature_matrix import file_sha256


def _prediction_frame(split_id: str, date: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "outer_split_id": [split_id, split_id],
            "datetime": [date, date],
            "instrument": ["SH600000", "SZ000001"],
            "method": ["lightgbm", "lightgbm"],
            "prediction": [0.2, 0.1],
            "prediction_artifact_id": [f"prediction:{split_id}"] * 2,
            "allowlist_sha256": ["a" * 64] * 2,
            "feature_order_sha256": ["b" * 64] * 2,
            "model_freeze_id": [f"freeze:{split_id}"] * 2,
            "experiment_class": ["post_observation_research"] * 2,
        }
    )


@pytest.fixture
def prediction_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(backtest, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(backtest, "_validated_manifest", lambda path, role: {"artifact_id": role})
    dates = {
        "split_001": "2024-08-01",
        "split_002": "2025-02-05",
        "split_003": "2025-08-05",
    }
    receipts = []
    assignments = []
    for split_id, date in dates.items():
        path = tmp_path / f"{split_id}.parquet"
        frame = _prediction_frame(split_id, date)
        frame.to_parquet(path, index=False)
        receipts.append(
            {
                "outer_split_id": split_id,
                "method": "lightgbm",
                "prediction_artifact_id": f"prediction:{split_id}",
                "prediction_row_count": len(frame),
                "prediction_sha256": file_sha256(path),
                "runtime_path": str(path),
                "schema_sha256": "c" * 64,
                "prediction_coverage": 1.0,
            }
        )
        assignments.append({"outer_split_id": split_id, "fold": "test", "datetime": date})
    pd.DataFrame(receipts).to_csv(tmp_path / "receipt.csv", index=False)
    pd.DataFrame(assignments).to_csv(tmp_path / "dates.csv", index=False)
    config = {
        "prediction_manifest": "manifest.json",
        "prediction_receipt": "receipt.csv",
        "date_assignments": "dates.csv",
    }
    return config, dates


def _rewrite_receipt_hash(root: Path, split_id: str) -> None:
    receipt = pd.read_csv(root / "receipt.csv")
    path = root / f"{split_id}.parquet"
    mask = receipt["outer_split_id"].eq(split_id)
    receipt.loc[mask, "prediction_sha256"] = file_sha256(path)
    receipt.loc[mask, "prediction_row_count"] = len(pd.read_parquet(path))
    receipt.to_csv(root / "receipt.csv", index=False)


def test_three_prediction_files_are_required(prediction_fixture, tmp_path: Path) -> None:
    config, _ = prediction_fixture
    (tmp_path / "split_003.parquet").unlink()
    with pytest.raises(FileNotFoundError, match="do not regenerate"):
        backtest.audit_prediction_inputs(config)


def test_prediction_hash_mismatch_is_blocked(prediction_fixture, tmp_path: Path) -> None:
    config, _ = prediction_fixture
    path = tmp_path / "split_002.parquet"
    path.write_bytes(path.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="hash mismatch"):
        backtest.audit_prediction_inputs(config)


def test_prediction_duplicate_key_is_blocked(prediction_fixture, tmp_path: Path) -> None:
    config, _ = prediction_fixture
    path = tmp_path / "split_001.parquet"
    frame = pd.read_parquet(path)
    pd.concat([frame, frame.iloc[[0]]], ignore_index=True).to_parquet(path, index=False)
    _rewrite_receipt_hash(tmp_path, "split_001")
    with pytest.raises(ValueError, match="duplicate"):
        backtest.audit_prediction_inputs(config)


def test_prediction_date_outside_exact_test_fold_is_blocked(
    prediction_fixture, tmp_path: Path
) -> None:
    config, _ = prediction_fixture
    path = tmp_path / "split_003.parquet"
    frame = pd.read_parquet(path)
    frame["datetime"] = "2025-08-06"
    frame.to_parquet(path, index=False)
    _rewrite_receipt_hash(tmp_path, "split_003")
    with pytest.raises(ValueError, match="escape exact test"):
        backtest.audit_prediction_inputs(config)


def test_valid_frozen_predictions_are_loaded_without_regeneration(
    prediction_fixture,
) -> None:
    config, _ = prediction_fixture
    receipt, predictions, _ = backtest.audit_prediction_inputs(config)
    assert set(predictions) == set(backtest.SPLITS)
    assert receipt["predictions_regenerated"].eq(False).all()


@pytest.mark.parametrize(
    ("interval", "expected"),
    [(5, [0, 5, 10, 15]), (20, [0])],
)
def test_rebalance_schedule_has_no_off_by_one(interval: int, expected: list[int]) -> None:
    dates = pd.bdate_range("2026-01-05", periods=20)
    selected = rebalance_execution_dates(dates, interval)
    assert selected.tolist() == dates[expected].tolist()


def test_signal_at_t_first_executes_at_t_plus_one() -> None:
    calendar = pd.bdate_range("2026-01-05", periods=6)
    signal_dates = calendar[:-1]
    execution_dates = calendar[1:]
    assert (execution_dates - signal_dates).days.min() >= 1
    assert rebalance_execution_dates(execution_dates, 5)[0] == calendar[1]


def test_non_rebalance_day_keeps_previous_target() -> None:
    selector = PeriodicEqualWeightSelector(top_k=2, rebalance_interval=5)
    dates = pd.bdate_range("2026-01-05", periods=6)
    first = selector.select(pd.Series({"A": 3.0, "B": 2.0, "C": 1.0}), dates[0])
    second = selector.select(pd.Series({"C": 3.0, "B": 2.0, "A": 1.0}), dates[1])
    for value in dates[2:5]:
        selector.select(pd.Series({"C": 3.0, "B": 2.0, "A": 1.0}), value)
    sixth = selector.select(pd.Series({"C": 3.0, "B": 2.0, "A": 1.0}), dates[5])
    assert first == {"A": 0.5, "B": 0.5}
    assert second is None
    assert sixth == {"C": 0.5, "B": 0.5}


def test_top_k_equal_weight_is_deterministic() -> None:
    target = equal_weight_targets(pd.Series({"C": 1.0, "A": 3.0, "B": 2.0}), 2)
    assert target == {"A": 0.5, "B": 0.5}


def test_t_plus_one_and_cost_components_remain_active() -> None:
    ledger = TPlusOneLedger()
    ledger.start_day(pd.Timestamp("2026-01-06"), {"SH600000": 100})
    ledger.record_fill("SH600000", "buy", 200)
    assert ledger.clip_sell("SH600000", 300) == (100, 200)
    costs = component_costs(
        side="sell",
        gross_value=100_000,
        executed_shares=10_000,
        base_price=10.0,
        fill_price=9.99,
        commission_rate=0.0003,
        sell_tax_rate=0.001,
        minimum_commission=5.0,
    )
    assert costs.commission == pytest.approx(30.0)
    assert costs.stamp_tax == pytest.approx(100.0)
    assert costs.slippage_cost == pytest.approx(100.0)


def _development_results() -> pd.DataFrame:
    rows = []
    for index, portfolio_id in enumerate([f"P{i:02d}" for i in range(1, 7)], start=1):
        top_k = [50, 100, 200, 50, 100, 200][index - 1]
        interval = 5 if index <= 3 else 20
        for split_id in backtest.DEVELOPMENT_SPLITS:
            rows.append(
                {
                    "portfolio_id": portfolio_id,
                    "outer_split_id": split_id,
                    "top_k": top_k,
                    "rebalance_interval": interval,
                    "information_ratio": float(7 - index),
                    "annualized_excess_return": float(7 - index) / 10,
                    "average_daily_turnover": float(index) / 10,
                }
            )
    return pd.DataFrame(rows)


def test_portfolio_selection_uses_only_two_development_splits() -> None:
    selected = backtest.select_portfolio_rule(_development_results())
    assert selected["selected_portfolio_id"] == "P01"
    assert selected["development_splits"] == ["split_001", "split_002"]
    assert selected["holdout_execution_count_at_selection"] == 0
    assert selected["holdout_performance_read_count_at_selection"] == 0


def test_holdout_rows_are_rejected_from_candidate_selection() -> None:
    contaminated = pd.concat(
        [
            _development_results(),
            pd.DataFrame(
                [
                    {
                        "portfolio_id": "P06",
                        "outer_split_id": "split_003",
                        "top_k": 200,
                        "rebalance_interval": 20,
                        "information_ratio": 999.0,
                        "annualized_excess_return": 999.0,
                        "average_daily_turnover": 0.0,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    with pytest.raises(ValueError, match="exactly 6 x 2"):
        backtest.select_portfolio_rule(contaminated)


def test_holdout_relative_advantage_requires_positive_holdout_excess() -> None:
    performance = pd.DataFrame(
        [
            {"portfolio_id": "P01", "outer_split_id": "split_001", "annualized_excess_return": 0.8},
            {"portfolio_id": "P01", "outer_split_id": "split_002", "annualized_excess_return": 0.4},
            {"portfolio_id": "P01", "outer_split_id": "split_003", "annualized_excess_return": -0.3},
        ]
    )
    assert not backtest.holdout_supported_relative_advantage(
        performance, {"selected_portfolio_id": "P01"}
    )
    contract = backtest.completion_contract(
        performance, {"selected_portfolio_id": "P01"}
    )
    row = contract.loc[
        contract["check_name"].eq(
            "portfolio_holdout_supported_relative_advantage"
        )
    ].iloc[0]
    assert row["observed_value"] == False  # noqa: E712


def test_each_scenario_keeps_independent_initial_cash() -> None:
    development = _development_results()
    development["initial_nav"] = 10_000_000.0
    assert development.groupby("outer_split_id")["initial_nav"].first().eq(10_000_000.0).all()


def test_stale_valuation_fallback_is_past_only_and_recorded() -> None:
    market = pd.DataFrame(
        {
            "datetime": pd.date_range("2026-01-05", periods=3),
            "instrument": ["SH600000"] * 3,
            "close": [10.0, np.nan, np.nan],
            "valuation_stale_blocked": [False, True, True],
        }
    )
    result = backtest.apply_research_valuation_fallback(
        market, policy="carry_last_valid_close"
    )
    assert result["close"].tolist() == [10.0, 10.0, 10.0]
    assert result["research_valuation_fallback_applied"].tolist() == [False, True, True]


def test_market_audit_is_scoped_to_consumed_dates() -> None:
    market = pd.DataFrame(
        {
            "datetime": pd.date_range("2026-01-05", periods=2),
            "instrument": ["SH600000", "SH600000"],
            "research_valuation_fallback_applied": [False, True],
            "valuation_price_age_trading_days": [0, 21],
            "market_semantics_authoritative": [False, False],
        }
    )
    audit = backtest.summarize_market_scope(market.iloc[[0]], {"market_sha256": "a" * 64})
    assert audit["stale_valuation_date_count"] == 0
    assert audit["unknown_tradability_count"] == 1
    assert audit["market_sha256"] == "a" * 64


def test_backtest_module_does_not_call_model_training() -> None:
    source = inspect.getsource(backtest)
    assert "lightgbm.train" not in source
    assert "Booster(" not in source
    assert "predict(" not in source


def test_synthetic_metrics_include_costs_and_benchmark() -> None:
    dates = pd.bdate_range("2026-01-05", periods=3)
    result = {
        "daily_accounting": pd.DataFrame(
            {
                "datetime": dates,
                "nav": [10_000_000, 10_100_000, 10_050_000],
                "return": [0.0, 0.01, -0.004950495],
                "turnover": [0.5, 0.1, 0.0],
            }
        ),
        "orders": pd.DataFrame({"requested_shares": [1000], "executed_shares": [900]}),
        "fills": pd.DataFrame({"event_id": ["e1"]}),
        "partial_fills": pd.DataFrame({"event_id": ["e1"]}),
        "rejected_orders": pd.DataFrame(),
        "transaction_costs": pd.DataFrame(
            {"datetime": [dates[0]], "commission": [10.0], "stamp_tax": [5.0], "slippage_cost": [20.0], "implementation_cost": [35.0]}
        ),
        "positions": pd.DataFrame(
            {"datetime": dates, "instrument": ["SH600000"] * 3, "weight": [0.5, 0.5, 0.5]}
        ),
    }
    benchmark = pd.DataFrame({"datetime": dates, "benchmark_close": [1, 1.01, 1.0], "benchmark_return": [0.0, 0.01, -0.00990099]})
    market = pd.DataFrame({"datetime": dates, "instrument": ["SH600000"] * 3, "research_valuation_fallback_applied": [False] * 3})
    summary, daily, monthly, _ = backtest.calculate_scenario_metrics(
        result=result,
        benchmark=benchmark,
        market=market,
        market_audit={"stale_valuation_date_count": 0, "stale_valuation_instrument_count": 0, "maximum_stale_days": 0, "affected_instruments": "", "unknown_tradability_count": 0},
        receipt_row={"prediction_coverage": 0.99},
        portfolio={"portfolio_id": "P02", "top_k": 100, "rebalance_interval": 5},
        split_id="split_001",
        initial_cash=10_000_000,
    )
    assert summary["fill_rate"] == pytest.approx(0.9)
    assert summary["total_transaction_cost"] == pytest.approx(35.0)
    assert summary["gross_return_approx"] > summary["total_return"]
    assert daily.loc[0, "drawdown"] == pytest.approx(0.0)
    assert len(daily) == 3 and len(monthly) == 1


def test_first_day_loss_is_included_in_drawdown() -> None:
    dates = pd.bdate_range("2026-01-05", periods=2)
    result = {
        "daily_accounting": pd.DataFrame(
            {
                "datetime": dates,
                "nav": [9_900_000, 9_800_000],
                "return": [-0.01, -0.01010101],
                "turnover": [0.0, 0.0],
            }
        ),
        "orders": pd.DataFrame(),
        "fills": pd.DataFrame(),
        "partial_fills": pd.DataFrame(),
        "rejected_orders": pd.DataFrame(),
        "transaction_costs": pd.DataFrame(),
        "positions": pd.DataFrame(),
    }
    benchmark = pd.DataFrame(
        {
            "datetime": dates,
            "benchmark_close": [1.0, 1.0],
            "benchmark_return": [0.0, 0.0],
        }
    )
    market = pd.DataFrame(
        {
            "datetime": dates,
            "instrument": ["SH600000"] * 2,
            "research_valuation_fallback_applied": [False] * 2,
        }
    )
    summary, daily, _, _ = backtest.calculate_scenario_metrics(
        result=result,
        benchmark=benchmark,
        market=market,
        market_audit={
            "stale_valuation_date_count": 0,
            "stale_valuation_instrument_count": 0,
            "maximum_stale_days": 0,
            "affected_instruments": "",
            "unknown_tradability_count": 0,
        },
        receipt_row={"prediction_coverage": 1.0},
        portfolio={"portfolio_id": "P02", "top_k": 100, "rebalance_interval": 5},
        split_id="split_001",
        initial_cash=10_000_000,
    )
    assert daily.loc[0, "drawdown"] == pytest.approx(-0.01)
    assert summary["max_drawdown"] == pytest.approx(-0.02)
