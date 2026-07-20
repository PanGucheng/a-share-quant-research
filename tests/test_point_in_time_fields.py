from __future__ import annotations

import pandas as pd

from data_adapters.point_in_time_fields import audit_pit_fields, current_spot_to_pit


def test_current_snapshot_is_forward_only() -> None:
    raw = pd.DataFrame({"代码": ["600000"], "总市值": [100], "流通市值": [80]})
    fields = current_spot_to_pit(raw, pd.Timestamp("2026-07-12"), "id")
    assert fields.instrument.iloc[0] == "SH600000"
    assert not fields.historical_research_eligible.any()
    assert audit_pit_fields(fields)["historical_current_snapshot_backfill_count"] == 0


def test_historical_backfill_without_announcement_is_rejected() -> None:
    raw = pd.DataFrame({"代码": ["600000"], "总市值": [100], "流通市值": [80]})
    fields = current_spot_to_pit(raw, pd.Timestamp("2026-07-12"), "id")
    fields["historical_research_eligible"] = True; fields["effective_from"] = pd.Timestamp("2021-01-01")
    assert audit_pit_fields(fields)["historical_current_snapshot_backfill_count"] == len(fields)
