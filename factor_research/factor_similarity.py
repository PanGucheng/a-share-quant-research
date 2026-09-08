from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr


def pair_spearman_reference(left, right, minimum=50):
    """Exact finite-intersection oracle; no labels, dates or preprocessing policy."""
    left, right = np.asarray(left, dtype=float), np.asarray(right, dtype=float)
    mask = np.isfinite(left) & np.isfinite(right)
    count = int(mask.sum())
    if count < minimum:
        return np.nan, count, 1  # insufficient common samples
    a, b = left[mask], right[mask]
    if np.ptp(a) == 0 or np.ptp(b) == 0:
        return np.nan, count, 2  # constant on the intersection
    return float(spearmanr(a, b).statistic), count, 0


def daily_pairwise_spearman(values, minimum=50, *, engine="auto"):
    """Exact daily matrix with finite counts and reasons (0 valid/1 short/2 constant).

    Columns sharing a finite mask share SciPy ranks. Different mask groups are
    reranked on their intersection. Many tiny mask groups use pandas' exact
    pairwise implementation instead; it is not global pre-ranking plus deletion.
    """
    x = np.asarray(values, dtype=np.float64)
    if x.ndim != 2 or not x.shape[0] or not x.shape[1] or minimum < 2:
        raise ValueError("nonempty samples by features and minimum >= 2 required")
    if engine not in {"auto", "grouped", "pandas"}:
        raise ValueError("unknown Spearman engine")
    finite = np.isfinite(x)
    groups = {}
    for j in range(x.shape[1]):
        groups.setdefault(np.packbits(finite[:, j]).tobytes(), []).append(j)
    integer_masks = finite.astype(np.int32)
    common = (integer_masks.T @ integer_masks).astype(np.uint32)
    rho = np.full(common.shape, np.nan)
    selected = "pandas" if engine == "pandas" or (engine == "auto" and len(groups) > 64) else "grouped"
    if selected == "pandas":
        clean = np.where(finite, x, np.nan)
        rho = pd.DataFrame(clean).corr(method="spearman", min_periods=minimum).to_numpy()
    else:
        columns = list(groups.values())
        for g, left in enumerate(columns):
            for right in columns[g:]:
                mask = finite[:, left[0]] & finite[:, right[0]]
                if mask.sum() < minimum:
                    continue
                a = rankdata(x[np.ix_(mask, left)], axis=0, method="average")
                b = a if left is right else rankdata(x[np.ix_(mask, right)], axis=0, method="average")
                a = a - a.mean(axis=0)
                b = b - b.mean(axis=0)
                denom = np.linalg.norm(a, axis=0)[:, None] * np.linalg.norm(b, axis=0)[None, :]
                block = np.divide(a.T @ b, denom, out=np.full(denom.shape, np.nan), where=denom > 0)
                rho[np.ix_(left, right)] = block
                rho[np.ix_(right, left)] = block.T
    rho = np.clip(rho, -1, 1)
    reason = np.where(common < minimum, 1, np.where(np.isfinite(rho), 0, 2)).astype(np.uint8)
    return {"rho": rho, "n_common": common, "reason": reason,
            "finite_count": finite.sum(axis=0).astype(np.uint32),
            "infinite_count": np.isinf(x).sum(axis=0).astype(np.uint32),
            "universe_count": len(x), "mask_groups": len(groups), "engine": selected}


def _filter_allowed_dates(frame: pd.DataFrame, allowed_dates: pd.DatetimeIndex | list[pd.Timestamp] | None) -> pd.DataFrame:
    if allowed_dates is None:
        raise ValueError("allowed_dates is required for holdout-clean similarity")
    allowed = pd.DatetimeIndex(allowed_dates).normalize().unique()
    values = frame.copy()
    values["datetime"] = pd.to_datetime(values["datetime"]).dt.normalize()
    return values.loc[values["datetime"].isin(allowed)].copy()


def daily_exposure_similarity(
    frame: pd.DataFrame,
    factor_map: dict[str, str],
    max_dates: int | None = None,
    *,
    allowed_dates: pd.DatetimeIndex | list[pd.Timestamp] | None = None,
    minimum_pair_observations: int = 20,
) -> pd.DataFrame:
    data = frame[["datetime", "instrument", *sorted(set(factor_map.values()))]].copy()
    data = _filter_allowed_dates(data, allowed_dates)
    dates = sorted(data["datetime"].dropna().unique())
    if max_dates and len(dates) > max_dates:
        positions = np.linspace(0, len(dates) - 1, max_dates, dtype=int)
        dates = [dates[position] for position in positions]
    matrices = []
    for date in dates:
        cross = data.loc[data["datetime"] == date, sorted(set(factor_map.values()))]
        if len(cross) >= 20:
            matrices.append(cross.corr(method="spearman", min_periods=minimum_pair_observations))
    if not matrices:
        raise ValueError("no eligible cross-sections for exposure similarity")
    base = pd.concat(matrices, keys=range(len(matrices))).groupby(level=1).median()
    factors = list(factor_map)
    result = pd.DataFrame(index=factors, columns=factors, dtype=float)
    for left in factors:
        for right in factors:
            result.loc[left, right] = base.loc[factor_map[left], factor_map[right]]
    return result


def performance_similarity(
    series_map: dict[str, pd.Series],
    *,
    allowed_dates: pd.DatetimeIndex | list[pd.Timestamp] | None = None,
    minimum_pair_dates: int = 20,
) -> pd.DataFrame:
    if allowed_dates is None:
        raise ValueError("allowed_dates is required for holdout-clean similarity")
    allowed = pd.DatetimeIndex(allowed_dates).normalize().unique()
    aligned = pd.concat({name: series for name, series in series_map.items()}, axis=1)
    aligned.index = pd.to_datetime(aligned.index).normalize()
    aligned = aligned.loc[aligned.index.isin(allowed)]
    return aligned.corr(method="spearman", min_periods=minimum_pair_dates)


def combined_distance(exposure: pd.DataFrame, performance: pd.DataFrame, exposure_weight: float) -> pd.DataFrame:
    factors = sorted(set(exposure.index) & set(performance.index))
    exp = exposure.loc[factors, factors].abs().fillna(0)
    perf = performance.loc[factors, factors].abs().fillna(0)
    similarity = exposure_weight * exp + (1 - exposure_weight) * perf
    distance = 1 - similarity.clip(0, 1)
    np.fill_diagonal(distance.values, 0.0)
    return distance
