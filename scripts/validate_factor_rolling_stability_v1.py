from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.rolling_evaluation import select_factor_window, stability_board


def main() -> int:
    valid = pd.Series({"factor": "a", "split_id": "s", "train_mean_ic": 0.03, "validation_mean_ic": 0.02, "train_count": 100, "validation_count": 50, "fdr_bh_pass": True, "fdr_bh_q_value": 0.01})
    assert select_factor_window(valid, min_abs_validation_ic=0.01, min_dates=40)["selected"]
    try:
        select_factor_window(pd.concat([valid, pd.Series({"test_mean_ic": 1.0})]), min_abs_validation_ic=0.01, min_dates=40)
    except ValueError:
        pass
    else:
        raise AssertionError("test metric was accepted by selection")
    rows = pd.DataFrame([{"factor": "a", "selected": True, "eligible": True, "frozen_direction": 1, "train_mean_ic": 0.03, "validation_mean_ic": 0.02, "test_mean_ic": 0.01, "fdr_bh_pass": True, "train_coverage": 1.0, "validation_coverage": 1.0, "test_coverage": 1.0}] * 3)
    assert stability_board(rows).iloc[0].stability_role == "stable_core"
    print("All rolling stability synthetic validations passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
