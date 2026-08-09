from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from daily_update.pipeline import (
    NotReady,
    baostock_release_window_open,
    bridge_baostock_to_community,
    collect_baostock_range,
    compatibility_smoke,
    validate_baostock_target,
)


def _bao_row(day: str = "2026-08-07") -> pd.DataFrame:
    return pd.DataFrame([
        {
            "date": day, "code": "sh.600000", "open": "10.0", "high": "10.5",
            "low": "9.8", "close": "10.2", "preclose": "10.0", "volume": "10000",
            "amount": "102000", "adjustflag": "3", "tradestatus": "1", "isST": "0",
        }
    ])


def test_empty_baostock_day_is_safe_not_ready() -> None:
    with pytest.raises(NotReady, match="has not published"):
        validate_baostock_target(pd.DataFrame(), date(2026, 8, 7), ["SH600000"], 0.95)


def test_baostock_waits_for_adjustment_factor_window() -> None:
    shanghai = ZoneInfo("Asia/Shanghai")
    assert not baostock_release_window_open(
        date(2026, 8, 7), datetime(2026, 8, 7, 17, 59, tzinfo=shanghai)
    )
    assert baostock_release_window_open(
        date(2026, 8, 7), datetime(2026, 8, 7, 18, 0, tzinfo=shanghai)
    )


def test_baostock_range_uses_one_batch_call_per_date(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    fake_baostock = SimpleNamespace(
        login=lambda: SimpleNamespace(error_code="0", error_msg="success"),
        logout=lambda: SimpleNamespace(error_code="0", error_msg="success"),
    )
    monkeypatch.setitem(__import__("sys").modules, "baostock", fake_baostock)

    def fake_daily(day: str) -> tuple[pd.DataFrame, str]:
        calls.append(day)
        return _bao_row(day), "success"

    monkeypatch.setattr("daily_update.sources.baostock.collect_daily_all", fake_daily)
    frame, failures = collect_baostock_range(date(2026, 8, 6), date(2026, 8, 7))
    assert calls == ["2026-08-06", "2026-08-07"]
    assert len(frame) == 2
    assert failures == []


def test_baostock_factor_probe_retries_one_transient_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from daily_update.sources import baostock as source

    fake_baostock = SimpleNamespace(
        login=lambda: SimpleNamespace(error_code="0", error_msg="success"),
        logout=lambda: SimpleNamespace(error_code="0", error_msg="success"),
    )
    monkeypatch.setitem(__import__("sys").modules, "baostock", fake_baostock)
    calls = []

    def fake_factor(_day: str) -> tuple[pd.DataFrame, str]:
        calls.append(_day)
        if len(calls) == 1:
            return pd.DataFrame(), "transient socket error"
        return pd.DataFrame([{"code": "sh.600000"}]), "success"

    monkeypatch.setattr(source, "collect_daily_adjust_factor", fake_factor)
    monkeypatch.setattr(source.time_module, "sleep", lambda _seconds: None)

    frame, status = source.collect_baostock_factor_once(date(2026, 8, 7))

    assert status == "success"
    assert len(frame) == 1
    assert calls == ["2026-08-07", "2026-08-07"]


def test_incomplete_coverage_is_safe_not_ready() -> None:
    with pytest.raises(NotReady, match="coverage"):
        validate_baostock_target(
            _bao_row(), date(2026, 8, 7), ["SH600000", "SZ000001"], 0.95
        )


def test_factor_bridge_preserves_community_semantics() -> None:
    anchor = pd.DataFrame({"raw_close": [10.0], "$factor": [0.1]}, index=["SH600000"])
    bridged = bridge_baostock_to_community(_bao_row(), anchor).iloc[0]
    assert bridged["factor"] == pytest.approx(0.1)
    assert bridged["close"] == pytest.approx(1.02)
    assert bridged["volume"] == pytest.approx(1000.0)
    assert bridged["amount"] == pytest.approx(102.0)
    assert bridged["vwap"] == pytest.approx(1.02)
    assert np.isfinite(bridged[["open", "high", "low", "close", "volume", "amount"]].astype(float)).all()


def test_factor_bridge_handles_corporate_action_preclose() -> None:
    raw = _bao_row()
    raw.loc[0, "preclose"] = "5.0"
    anchor = pd.DataFrame({"raw_close": [10.0], "$factor": [0.1]}, index=["SH600000"])
    bridged = bridge_baostock_to_community(raw, anchor).iloc[0]
    assert bridged["factor"] == pytest.approx(0.2)
    assert bridged["bridge_mode"] == "community_anchor_preclose_bridge"


def test_compatibility_smoke_fails_closed_on_factor_difference() -> None:
    daily = pd.DataFrame([{
        "symbol": "SH600000", "raw_open": 10.0, "raw_high": 10.5,
        "raw_low": 9.8, "raw_close": 10.2, "raw_volume": 10000.0,
        "raw_amount": 102000.0, "factor": 0.1,
    }])
    features = pd.DataFrame([{
        "datetime": pd.Timestamp("2026-08-07"), "instrument": "SH600000", "f1": 1.0,
    }])
    passed = compatibility_smoke(daily, daily.copy(), features, features.copy())
    assert passed["status"] == "pass"
    changed = features.copy()
    changed["f1"] = 1.1
    blocked = compatibility_smoke(daily, daily.copy(), features, changed)
    assert blocked["status"] == "blocked_material_difference"
