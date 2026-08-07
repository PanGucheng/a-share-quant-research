from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from daily_update.forward_adapter import FORWARD_COLUMNS, prepare_forward_inputs


def _daily_dir(tmp_path: Path) -> Path:
    target = tmp_path / "2026-08-07"
    target.mkdir()
    (target / "summary.json").write_text(
        json.dumps(
            {
                "status": "ready",
                "target_date": "2026-08-07",
                "factor_count": 52,
                "source": "baostock",
                "raw_snapshot_first_seen_at": "2026-08-07T11:30:00+00:00",
                "feature_snapshot_created_at": "2026-08-07T11:40:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {
                "date": "2026-08-07",
                "symbol": "sh600000",
                "open": 1.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.05,
                "volume": 100.0,
                "amount": 105.0,
            }
        ]
    ).to_csv(target / "baostock_qlib_daily.csv", index=False)
    pd.DataFrame(
        [{"datetime": "2026-08-07", "instrument": "SH600000", "f1": 1.0}]
    ).to_csv(target / "feature_snapshot.csv", index=False)
    return target


def test_prepare_forward_inputs_maps_qlib_schema(tmp_path: Path) -> None:
    target = _daily_dir(tmp_path)
    result = prepare_forward_inputs(target, decision_date="2026-08-07")
    raw = pd.read_csv(result["raw_path"])
    assert tuple(raw.columns) == FORWARD_COLUMNS
    assert raw.loc[0, "instrument"] == "SH600000"
    assert result["raw_snapshot_first_seen_at"] == "2026-08-07T11:30:00+00:00"
    metadata = json.loads(Path(result["metadata_path"]).read_text(encoding="utf-8"))
    assert metadata["label_read_count"] == 0


def test_prepare_forward_inputs_rejects_wrong_date(tmp_path: Path) -> None:
    target = _daily_dir(tmp_path)
    with pytest.raises(ValueError, match="summary is not ready"):
        prepare_forward_inputs(target, decision_date="2026-08-06")


def test_prepare_forward_inputs_maps_suspended_empty_volume_to_zero(tmp_path: Path) -> None:
    target = _daily_dir(tmp_path)
    daily_path = target / "baostock_qlib_daily.csv"
    daily = pd.read_csv(daily_path)
    daily.loc[0, ["open", "high", "low", "close"]] = 1.0
    daily.loc[0, ["volume", "amount"]] = pd.NA
    daily.to_csv(daily_path, index=False)
    result = prepare_forward_inputs(target, decision_date="2026-08-07")
    raw = pd.read_csv(result["raw_path"])
    assert raw.loc[0, "$volume"] == 0.0
    assert raw.loc[0, "$amount"] == 0.0
    metadata = json.loads(Path(result["metadata_path"]).read_text(encoding="utf-8"))
    assert metadata["suspended_zero_fill_instruments"] == ["SH600000"]


def test_prepare_forward_inputs_uses_community_daily_file(tmp_path: Path) -> None:
    target = _daily_dir(tmp_path)
    summary_path = target / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["source"] = "community"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    (target / "baostock_qlib_daily.csv").rename(target / "community_qlib_daily.csv")

    result = prepare_forward_inputs(target, decision_date="2026-08-07")
    raw = pd.read_csv(result["raw_path"])
    assert raw.loc[0, "instrument"] == "SH600000"
