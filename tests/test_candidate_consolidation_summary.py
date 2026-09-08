import numpy as np
import pandas as pd

from factor_research.candidate_consolidation_summary import reduce_pairs, stable_annotations, view_masks


def test_daily_weighting_missing_sign_and_overlap():
    rho = np.array([[.9, np.nan], [.9, np.nan], [-.9, np.nan], [-.9, np.nan], [-.8, np.nan]])
    common = np.full(rho.shape, 60)
    reasons = np.where(np.isfinite(rho), 0, 1)
    finite = np.full(rho.shape, 80)
    result = reduce_pairs(rho, common, reasons, finite, finite, np.full(5, 100))
    assert result.median_signed_rho.iloc[0] == -.8
    assert result.median_abs_rho.iloc[0] == .9
    assert result.sign_consistency.iloc[0] == .6
    assert result.q10_common_coverage.iloc[0] == .6
    assert result.mean_jaccard.iloc[0] == .6
    assert not result.comparable.iloc[1]
    assert np.isnan(result.median_abs_rho.iloc[1])
    assert result.insufficient_dates.iloc[1] == 5


def test_era_sign_flip_is_not_stable_and_unknown_remains_unknown():
    base = pd.DataFrame({"comparable": [True, False], "median_abs_rho": [.99, .99],
                         "q10_abs_rho": [.99, .99], "sign_consistency": [1., 1.], "dominant_sign": [1, 1]})
    views = {k: base.copy() for k in ("Full", "A", "B", "C", "D")}
    assert list(stable_annotations(views, .95)) == ["stable_redundancy", "insufficient_overlap"]
    views["D"]["dominant_sign"] = -1
    assert list(stable_annotations(views, .95)) == ["no_stable_redundancy", "insufficient_overlap"]
    masks = view_masks(pd.to_datetime(["2011-01-01", "2016-01-01", "2019-01-01", "2022-01-01"]))
    assert masks["LOO_A"].tolist() == [False, True, True, True]
