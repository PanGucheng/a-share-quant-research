from __future__ import annotations

import sys
from multiprocessing import freeze_support
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.schemas import (  # noqa: E402
    validate_factor_frame,
    validate_judgement_frame,
    validate_label_frame,
    validate_screening_frame,
    validate_tradability_frame,
    validate_universe_intervals,
)


def expect_failure(function, frame: pd.DataFrame) -> None:
    try:
        function(frame)
    except Exception:
        return
    raise AssertionError(f"{function.__name__} accepted an invalid frame")


def main() -> int:
    factor = pd.DataFrame({"datetime": ["2026-01-02", "2026-01-02"], "instrument": ["SH600000", "SZ000001"], "factor_a": [1.0, np.nan]})
    original = factor.copy(deep=True)
    validate_factor_frame(factor, ["factor_a"])
    pd.testing.assert_frame_equal(factor, original)
    expect_failure(lambda data: validate_factor_frame(data, ["factor_a"]), pd.concat([factor.iloc[[0]], factor.iloc[[0]]], ignore_index=True))
    bad_inf = factor.copy(); bad_inf.loc[0, "factor_a"] = np.inf
    expect_failure(lambda data: validate_factor_frame(data, ["factor_a"]), bad_inf)

    label = pd.DataFrame({"feature_time": ["2026-01-02"], "label_start_time": ["2026-01-05"], "label_end_time": ["2026-01-09"], "instrument": ["SH600000"], "label": [0.01]})
    validate_label_frame(label)
    bad_label = label.copy(); bad_label["label_start_time"] = bad_label["feature_time"]
    expect_failure(validate_label_frame, bad_label)

    tradability = pd.DataFrame({"can_buy": [True], "can_sell": [False], "tradability_score": [80.0], "liquidity_bucket": [4]})
    validate_tradability_frame(tradability)
    bad_tradability = tradability.copy(); bad_tradability["tradability_score"] = 101
    expect_failure(validate_tradability_frame, bad_tradability)

    universe = pd.DataFrame({"instrument": ["SH600000"], "start_date": ["2026-02-02"], "end_date": ["2026-02-27"], "selection_date": ["2026-01-30"], "effective_date": ["2026-02-02"], "selection_reason": ["top_amount"]})
    validate_universe_intervals(universe)
    overlap = pd.concat([universe, universe.assign(start_date="2026-02-20", end_date="2026-03-31")], ignore_index=True)
    expect_failure(validate_universe_intervals, overlap)

    screening = pd.DataFrame({"factor": ["factor_a"], "role": ["holdout"], "coverage": [0.9], "missing_rate": [0.1], "included": [False]})
    validate_screening_frame(screening)
    expect_failure(validate_screening_frame, screening.assign(included=True))

    judgement = pd.DataFrame({"factor": ["factor_a"], "judgement_role": ["new_source_alpha_probe"], "coverage": [0.9], "missing_rate": [0.1], "research_included": [True], "downstream_default_included": [False]})
    validate_judgement_frame(judgement)
    expect_failure(validate_judgement_frame, judgement.assign(downstream_default_included=True))
    print("All research data contract synthetic validations passed.")
    return 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
