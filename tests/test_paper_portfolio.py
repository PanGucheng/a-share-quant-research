from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

import model_research.paper_portfolio as paper


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[dict, Path]:
    prediction_root = tmp_path / "predictions"
    prediction_dir = prediction_root / "2026-08-07"
    prediction_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "datetime": ["2026-08-07"] * 60,
            "instrument": [f"SH{600000 + value:06d}" for value in range(60)],
            "score": list(range(60)),
        }
    ).to_csv(prediction_dir / "prediction.csv", index=False)
    _write_json(
        prediction_dir / "prediction_receipt.json",
        {"status": "pending_label", "evidence_eligible": True, "prediction_commit_sha": "a" * 40},
    )
    _write_json(tmp_path / "freeze.json", {"candidate_freeze_effective_time_utc": "2026-08-02T00:00:00+00:00"})
    calendar = tmp_path / "calendar.txt"
    calendar.write_text("2026-08-07\n2026-08-10\n2026-08-11\n", encoding="utf-8")
    monkeypatch.setattr(
        paper,
        "validate_prediction_freeze_receipt",
        lambda *args, **kwargs: {
            "decision_date": "2026-08-07",
            "label_start_date": "2026-08-10",
            "label_start_cutoff": "2026-08-10T09:25:00+08:00",
        },
    )
    config = {
        "candidate_freeze": str(tmp_path / "freeze.json"),
        "prediction_root": str(prediction_root),
        "daily_update_root": str(tmp_path / "daily"),
        "output_root": str(tmp_path / "paper"),
        "top_k": 50,
        "rebalance_interval": 5,
        "risk_degree": 0.95,
        "initial_cash": 10_000_000.0,
        "lot_size": 100,
        "dynamic_lot_rules": True,
        "buy_commission_rate": 0.0003,
        "sell_commission_rate": 0.0003,
        "sell_tax_rate": 0.001,
        "minimum_commission": 5.0,
        "slippage_bps": 10.0,
        "max_participation_rate": 0.05,
        "limit_threshold_approximation": 0.095,
        "trading_rules": str(paper.PROJECT_ROOT / "configs/a_share_trading_rules_v1.yaml"),
    }
    return config, calendar


def test_official_prediction_creates_p01_top50_pending_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, calendar = _fixture(tmp_path, monkeypatch)
    result = paper.create_paper_decision(
        config,
        decision_date="2026-08-07",
        calendar_path=calendar,
        repository_root=tmp_path,
        created_at=datetime(2026, 8, 7, 13, tzinfo=timezone.utc),
    )
    target = pd.read_csv(tmp_path / "paper/decisions/2026-08-07/target_weights.csv")
    state = json.loads((tmp_path / "paper/status.json").read_text(encoding="utf-8"))
    assert result["action"] == "rebalance"
    assert result["execution_date"] == "2026-08-10"
    assert len(target) == 50
    assert target["rank"].tolist() == list(range(1, 51))
    assert target["score"].is_monotonic_decreasing
    assert target["target_weight"].sum() == pytest.approx(1.0)
    assert target["target_stock_weight"].sum() == pytest.approx(0.95)
    assert set(target["instrument"]) == {f"SH{600000 + value:06d}" for value in range(10, 60)}
    assert state["pending_execution_dates"] == ["2026-08-10"]
    assert state["label_read_count"] == 0


def test_paper_decision_is_not_repeatable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, calendar = _fixture(tmp_path, monkeypatch)
    kwargs = {
        "decision_date": "2026-08-07",
        "calendar_path": calendar,
        "repository_root": tmp_path,
        "created_at": datetime(2026, 8, 7, 13, tzinfo=timezone.utc),
    }
    paper.create_paper_decision(config, **kwargs)
    with pytest.raises(FileExistsError, match="already exists"):
        paper.create_paper_decision(config, **kwargs)


def test_current_paper_config_reuses_frozen_historical_p01() -> None:
    config = paper.load_paper_config("configs/strategy_v1_paper_portfolio_v1.yaml")
    assert config["portfolio_id"] == "P01"
    assert config["top_k"] == 50
    assert config["rebalance_interval"] == 5
    assert config["risk_degree"] == 0.95


def test_execution_waits_for_next_day_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, calendar = _fixture(tmp_path, monkeypatch)
    paper.create_paper_decision(
        config,
        decision_date="2026-08-07",
        calendar_path=calendar,
        repository_root=tmp_path,
        created_at=datetime(2026, 8, 7, 13, tzinfo=timezone.utc),
    )
    assert paper.refresh_paper_execution(config)["status"] == "pending_execution"


def test_execution_reuses_qlib_runner_after_next_day_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, calendar = _fixture(tmp_path, monkeypatch)
    paper.create_paper_decision(
        config,
        decision_date="2026-08-07",
        calendar_path=calendar,
        repository_root=tmp_path,
        created_at=datetime(2026, 8, 7, 13, tzinfo=timezone.utc),
    )
    instruments = [f"SH{600000 + value:06d}" for value in range(60)]
    for date, price in (("2026-08-07", 10.0), ("2026-08-10", 10.1)):
        target = tmp_path / "daily" / date
        target.mkdir(parents=True)
        _write_json(target / "summary.json", {"status": "ready", "source": "baostock"})
        pd.DataFrame(
            {
                "date": date,
                "symbol": instruments,
                "raw_open": price,
                "raw_close": price,
                "raw_volume": 1_000_000.0,
                "raw_amount": 10_000_000.0,
                "factor": 1.0,
            }
        ).to_csv(target / "baostock_qlib_daily.csv", index=False)

    captured = {}

    def fake_runner(signal: pd.DataFrame, market: pd.DataFrame, run_config: dict):
        captured["signal"] = signal
        captured["market"] = market
        captured["config"] = run_config
        empty = pd.DataFrame()
        return {
            "fills": pd.DataFrame({"datetime": ["2026-08-10"], "instrument": ["SH600059"]}),
            "rejected_orders": empty,
            "positions": pd.DataFrame({"datetime": ["2026-08-10"], "instrument": ["SH600059"]}),
            "daily_accounting": pd.DataFrame({"datetime": ["2026-08-10"], "nav": [10_000_000.0]}),
        }

    monkeypatch.setattr(paper, "_run_qlib_execution", fake_runner)
    result = paper.refresh_paper_execution(config)
    assert result["executed_through"] == "2026-08-10"
    assert set(pd.to_datetime(captured["market"]["datetime"]).dt.strftime("%Y-%m-%d")) == {
        "2026-08-07",
        "2026-08-10",
    }
    assert captured["config"]["rebalance_interval"] == 5
    assert captured["market"]["lot_minimum_buy"].eq(100).all()
    assert (tmp_path / "paper/trades.csv").is_file()
    assert (tmp_path / "paper/positions.csv").is_file()
    assert (tmp_path / "paper/daily_nav.csv").is_file()
