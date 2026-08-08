from __future__ import annotations

import numpy as np
import pandas as pd

from model_research.style_attribution import (
    _controlled_alpha,
    _industry_exposure,
    _size_exposure,
)


def _style_frame() -> pd.DataFrame:
    rows = []
    for date in pd.to_datetime(["2026-01-02", "2026-01-03"]):
        for index, instrument in enumerate(["A", "B", "C", "D"], start=1):
            rows.append(
                {
                    "datetime": date,
                    "instrument": instrument,
                    "total_mv": float(index * 100),
                    "circ_mv": float(index * 80),
                    "size_percentile": index / 4,
                    "size_bucket": "Small" if index == 1 else "Large" if index == 4 else "Mid",
                    "sw_l1_code": "I1" if index <= 2 else "I2",
                    "sw_l1_name": "Industry 1" if index <= 2 else "Industry 2",
                }
            )
    return pd.DataFrame(rows)


def _base_frame() -> pd.DataFrame:
    frame = _style_frame()[["datetime", "instrument"]].copy()
    frame["prediction"] = frame["instrument"].map({"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0})
    return frame


def test_size_exposure_uses_daily_model_cohorts() -> None:
    base = _base_frame()
    second_date = base["datetime"].max()
    base.loc[base["datetime"].eq(second_date), "prediction"] = base.loc[
        base["datetime"].eq(second_date), "instrument"
    ].map({"A": 1.0, "B": 2.0, "C": 3.0, "D": 4.0})
    result = _size_exposure({"split_001": base}, _style_frame(), [2])
    top = result.loc[result["cohort"].eq("Top2")].iloc[0]
    universe = result.loc[result["cohort"].eq("Universe")].iloc[0]
    assert top["mean_size_percentile"] == 0.625
    assert top["small_share"] == 0.25
    assert top["mid_share"] == 0.5
    assert top["large_share"] == 0.25
    assert top[["small_share", "mid_share", "large_share"]].sum() == 1.0
    assert universe["mean_size_percentile"] == 0.625


def test_industry_exposure_reports_active_share_against_universe() -> None:
    result = _industry_exposure({"split_001": _base_frame()}, _style_frame(), [2])
    top_i1 = result.loc[(result["cohort"].eq("Top2")) & (result["sw_l1_code"].eq("I1"))].iloc[0]
    assert top_i1["mean_share"] == 1.0
    assert top_i1["mean_universe_share"] == 0.5
    assert top_i1["mean_active_share"] == 0.5


def test_controlled_alpha_recovers_model_coefficient_with_size_and_industry_controls() -> None:
    frames = []
    for day, date in enumerate(pd.date_range("2026-01-01", periods=3)):
        for index in range(40):
            score = (index - 19.5) / 10
            size = ((index * 7) % 40) / 39
            industry = "I1" if index % 2 == 0 else "I2"
            frames.append(
                {
                    "datetime": date,
                    "instrument": f"S{index:02d}",
                    "prediction": score,
                    "return_20d_t1": 0.03 * ((score - np.mean([(i - 19.5) / 10 for i in range(40)])) / np.std([(i - 19.5) / 10 for i in range(40)])) + 0.02 * ((size - np.mean([((i * 7) % 40) / 39 for i in range(40)])) / np.std([((i * 7) % 40) / 39 for i in range(40)])) + (0.01 if industry == "I2" else 0.0),
                    "size_percentile": size,
                    "sw_l1_code": industry,
                }
            )
    merged = pd.DataFrame(frames)
    base = merged[["datetime", "instrument", "prediction", "return_20d_t1"]]
    style = merged[["datetime", "instrument", "size_percentile", "sw_l1_code"]]
    _, summary = _controlled_alpha(
        {"minimum_daily_pairs": 30, "controlled_attribution": {"target": "return_20d_t1"}},
        {"split_001": base},
        style,
    )
    np.testing.assert_allclose(summary.loc[0, "mean_model_score_coefficient"], 0.03, atol=1e-12)
