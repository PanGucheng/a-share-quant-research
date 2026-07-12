from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.bootstrap import moving_block_mean_test
from research_validation.multiple_testing import apply_fdr


def main() -> int:
    rng = np.random.default_rng(7)
    stable = moving_block_mean_test(pd.Series(rng.normal(0.05, 0.1, 500)), samples=1000, block_length=20, seed=7)
    assert stable["raw_p_value"] < 0.05
    frame = pd.DataFrame({"factor": ["b", "a", "nan"], "test_family": ["x", "x", "x"], "metric": ["ic"] * 3, "raw_p_value": [0.01, 0.02, np.nan]})
    left = apply_fdr(frame, 0.05).sort_values("factor").reset_index(drop=True)
    right = apply_fdr(frame.iloc[::-1], 0.05).sort_values("factor").reset_index(drop=True)
    pd.testing.assert_series_equal(left["fdr_bh_q_value"], right["fdr_bh_q_value"])
    assert not left.loc[left.factor == "nan", "fdr_bh_pass"].iloc[0]
    print("All factor multiple-testing synthetic validations passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
