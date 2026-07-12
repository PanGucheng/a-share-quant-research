from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from data_adapters.point_in_time_fields import audit_pit_fields, current_spot_to_pit


def main() -> int:
    raw = pd.DataFrame({"代码": ["600000", "000001"], "总市值": [100, 200], "流通市值": [80, 160]})
    collected = pd.Timestamp("2026-07-12 10:00:00")
    fields = current_spot_to_pit(raw, collected, "snapshot")
    assert not fields.historical_research_eligible.any()
    assert (fields.effective_from == collected.normalize()).all()
    assert audit_pit_fields(fields)["historical_current_snapshot_backfill_count"] == 0
    print("All external exposure PIT synthetic validations passed."); return 0


if __name__ == "__main__": raise SystemExit(main())
