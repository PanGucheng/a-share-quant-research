"""Exact date-weighted reduction of sealed V0.5 daily arrays."""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from factor_research.candidate_consolidation import ERAS


def view_masks(dates):
    dates = pd.DatetimeIndex(dates)
    eras = {name: np.asarray((dates >= lo) & (dates <= hi)) for name, (lo, hi) in ERAS.items()}
    return {"Full": np.ones(len(dates), dtype=bool), **eras,
            **{f"LOO_{name}": ~mask for name, mask in eras.items()}}


def reduce_pairs(rho, common, reason, finite_left, finite_right, universe, *, minimum_fraction=.8, minimum_coverage=.5):
    """Columns are pairs, rows dates; Full never averages monthly/Era medians.

    Overlap distributions use valid-rho dates; all invalid dates remain counted.
    All-missing columns intentionally yield NaN, never zero similarity.
    """
    rho = np.asarray(rho, dtype=np.float64)
    valid = np.isfinite(rho)
    n = valid.sum(axis=0)
    if not len(rho) or np.any((reason == 0) != valid):
        raise ValueError("nonempty dates and consistent reason/rho required")
    coverage = common / np.asarray(universe)[:, None]
    union = finite_left.astype(np.int64) + finite_right.astype(np.int64) - common
    jaccard = np.divide(common, union, out=np.full(rho.shape, np.nan), where=union > 0)
    def fraction(count):
        return np.divide(count, n, out=np.full(n.shape, np.nan, dtype=float), where=n > 0)
    result = {"expected_dates": np.full(len(n), len(rho)), "valid_dates": n,
              "valid_date_fraction": n / len(rho),
              "insufficient_dates": (reason == 1).sum(axis=0),
              "constant_dates": (reason == 2).sum(axis=0),
              "positive_fraction": fraction((rho > 0).sum(axis=0)),
              "negative_fraction": fraction((rho < 0).sum(axis=0)),
              "zero_fraction": fraction((rho == 0).sum(axis=0))}
    result["sign_consistency"] = np.maximum(result["positive_fraction"], result["negative_fraction"])
    result["dominant_sign"] = np.sign(result["positive_fraction"] - result["negative_fraction"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # explicitly unavailable columns
        for name, values in (("signed_rho", rho), ("abs_rho", np.abs(rho)),
                             ("n_common", common), ("common_coverage", coverage), ("jaccard", jaccard)):
            values = np.where(valid, values, np.nan)
            result["mean_" + name] = np.nanmean(values, axis=0)
            result["median_" + name] = np.nanmedian(values, axis=0)
            result["q10_" + name] = np.nanquantile(values, .1, axis=0, method="linear")
            if name == "n_common":
                result["min_n_common"] = np.nanmin(values, axis=0)
    result["comparable"] = (result["valid_date_fraction"] >= minimum_fraction) & (result["q10_common_coverage"] >= minimum_coverage)
    return pd.DataFrame(result)


def stable_annotations(views, level, sign_threshold=.95):
    """No output-count tuning; unavailable Era evidence remains unknown."""
    required = [views[k] for k in ("Full", "A", "B", "C", "D")]
    comparable = np.logical_and.reduce([v.comparable.to_numpy() for v in required])
    strong = np.logical_and.reduce([(v.median_abs_rho >= level).to_numpy() &
                                    (v.q10_abs_rho >= level).to_numpy() &
                                    (v.sign_consistency >= sign_threshold).to_numpy() for v in required])
    signs = np.stack([v.dominant_sign.to_numpy() for v in required])
    same_sign = (signs == signs[0]).all(axis=0) & (signs[0] != 0)
    return np.where(~comparable, "insufficient_overlap",
                    np.where(strong & same_sign, "stable_redundancy", "no_stable_redundancy"))
