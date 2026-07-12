from __future__ import annotations

import sys
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.purged_split import WalkForwardConfig, build_purged_walk_forward, leakage_audit


def main() -> int:
    calendar = pd.bdate_range("2018-01-01", "2025-12-31")
    config = WalkForwardConfig(2, 3, 3, 3, 20, 1, 5, 300, 30, 40, "expanding")
    outputs = build_purged_walk_forward(calendar, config)
    assert (leakage_audit(outputs)["status"] == "pass").all()
    short = build_purged_walk_forward(calendar, WalkForwardConfig(2, 3, 3, 3, 1, 1, 5, 300, 30, 40, "expanding"))
    assert len(outputs["purged_dates"]) > len(short["purged_dates"])
    print("All purged walk-forward synthetic validations passed.")
    return 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
