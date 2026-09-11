"""D3-A pure statistics. The caller supplies the complete canonical session axis."""
from __future__ import annotations

import hashlib
import math

import numpy as np
import pandas as pd

ARMS = ('B', 'S', 'R', 'C', 'H')
CONTRASTS = ('S-B', 'R-B', 'C-B', 'H-B', 'C-R', 'H-C')


def common_day(labels, predictions, *, mature=True):
    """All columns share the same canonical row axis, never separate arm masks."""
    y = np.asarray(labels, dtype=np.float64)
    x = np.asarray(predictions, dtype=np.float64)
    if y.ndim != 1 or x.shape != (len(y), len(ARMS)) or not len(y):
        raise ValueError('invalid canonical daily array shape')
    finite_y = np.isfinite(y) & mature
    finite_x = np.isfinite(x)
    mask = finite_y & finite_x.all(axis=1)
    n = int(mask.sum())
    result = dict(canonical_count=len(y), mature=bool(mature),
                  mature_label_count=int(finite_y.sum()), common_count=n,
                  common_coverage=n / len(y),
                  common_over_finite_label=n / finite_y.sum() if finite_y.any() else np.nan,
                  **{f'finite_{a}': int(finite_x[:, i].sum()) for i, a in enumerate(ARMS)})
    reason = ('unscored_development_boundary' if not mature else
              'fewer_than_100_common_pairs' if n < 100 else '')
    ic = np.full(5, np.nan)
    if not reason:
        ranks = pd.DataFrame(np.column_stack([y[mask], x[mask]])).rank(method='average').to_numpy()
        ranks -= ranks.mean(axis=0)
        norms = np.sqrt((ranks * ranks).sum(axis=0))
        if (norms == 0).any():
            reason = 'constant_label_or_arm_on_common_sample'
        else:
            ic = np.clip(ranks[:, 0] @ ranks[:, 1:] / (norms[0] * norms[1:]), -1, 1)
    result.update(scoreable=not bool(reason), reason=reason or 'scoreable',
                  **{f'IC_{a}': float(ic[i]) for i, a in enumerate(ARMS)})
    for name in CONTRASTS:
        a, b = name.split('-')
        result[name] = result[f'IC_{a}'] - result[f'IC_{b}']
    return result, mask


def hac_mean(values, bandwidth):
    """Intercept sandwich; missing scores contribute zero on their original session."""
    x = np.asarray(values, dtype=np.float64)
    if x.ndim != 1 or bandwidth < 1:
        raise ValueError('invalid HAC input')
    valid = np.isfinite(x)
    n = int(valid.sum())
    mean = float(x[valid].mean()) if n else np.nan
    result = dict(mean=mean, n=n, bandwidth=bandwidth, se=np.nan, p=np.nan,
                  testable=False, reason='insufficient_dates')
    if n < 2:
        return result
    u = np.where(valid, x - mean, 0.0)
    if np.ptp(x[valid]) == 0:
        result.update(se=0.0, p=1.0 if mean == 0 else np.nan,
                      testable=mean == 0, reason='zero_delta' if mean == 0 else 'degenerate_variance')
        return result
    meat = float(u @ u)
    for lag in range(1, min(bandwidth + 1, len(x))):
        meat += 2 * (1 - lag / (bandwidth + 1)) * float(u[lag:] @ u[:-lag])
    # Bartlett kernel is PSD. Only a roundoff-scale negative may be clipped.
    if meat < -1e-12 * float(u @ u):
        raise ValueError('negative HAC variance')
    se = math.sqrt(max(meat, 0)) / n
    result.update(se=se, p=math.erfc(abs(mean) / se / math.sqrt(2)) if se > 0 else np.nan,
                  testable=se > 0, reason='testable' if se > 0 else 'degenerate_variance')
    return result


def holm_six(pvalues):
    p = np.asarray(pvalues, dtype=np.float64)
    if p.shape != (6,) or np.any(np.isfinite(p) & ((p < 0) | (p > 1))):
        raise ValueError('exactly six valid primary p-values required')
    effective = np.where(np.isfinite(p), p, 1.0)
    order = np.argsort(effective, kind='stable')
    adjusted = np.empty(6)
    adjusted[order] = np.minimum(1, np.maximum.accumulate(effective[order] * np.arange(6, 0, -1)))
    return adjusted


def block_support(valid, length):
    valid = np.asarray(valid, dtype=bool)
    if valid.ndim != 1 or length < 1:
        raise ValueError('invalid block input')
    positions = np.flatnonzero(valid)
    segments = np.split(positions, np.flatnonzero(np.diff(positions) != 1) + 1) if len(positions) else []
    starts = np.array([s for segment in segments if len(segment) >= length
                       for s in segment[:len(segment) - length + 1]], dtype=np.int64)
    unsupported = sum(len(segment) for segment in segments if len(segment) < length)
    available = len(positions) >= 2 * length and unsupported == 0 and len(starts) > 0
    return starts, dict(block_length=length, valid_dates=len(positions),
                        segment_lengths=[len(s) for s in segments],
                        unsupported_dates=unsupported,
                        unsupported_fraction=unsupported / len(positions) if len(positions) else None,
                        eligible_blocks=len(starts), available=bool(available),
                        reason='available' if available else 'insufficient_dates_or_unsupported_short_segment')


def sampled_indices(starts, n, length, rng):
    """One shared draw for the whole IC/delta matrix."""
    choices = rng.choice(starts, size=math.ceil(n / length), replace=True)
    return (choices[:, None] + np.arange(length)).ravel()[:n]


def moving_block_intervals(matrix, length, *, samples=1000, seed=20260909):
    x = np.asarray(matrix, dtype=np.float64)
    if x.ndim != 2 or samples < 2:
        raise ValueError('invalid bootstrap matrix')
    finite = np.isfinite(x)
    if not np.all(finite == finite[:, :1]):
        raise ValueError('all arms and contrasts must share scoreable dates')
    starts, support = block_support(finite.all(axis=1), length)
    support.update(samples=samples, seed=seed, interval='percentile_pointwise_not_simultaneous')
    ci = np.full((2, x.shape[1]), np.nan)
    if not support['available']:
        return ci, support
    rng = np.random.default_rng(seed)
    means = np.empty((samples, x.shape[1]))
    hasher = hashlib.sha256()
    for i in range(samples):
        indices = sampled_indices(starts, support['valid_dates'], length, rng)
        hasher.update(indices.astype('<i8').tobytes())
        means[i] = x[indices].mean(axis=0)
    ci[:] = np.quantile(means, [0.025, 0.975], axis=0)
    support['sampled_session_indices_sha256'] = hasher.hexdigest()
    return ci, support


def infer(daily):
    """Six fixed tests; all years remain required even if one is unscoreable."""
    if list(daily.datetime.dt.year.unique()) != list(range(2015, 2024)):
        raise ValueError('all nine prediction years required')
    eligible = all(part.scoreable.any() and all(part[f'finite_{a}'].sum() / part.canonical_count.sum() >= .95
                   for a in ARMS) for _, part in daily.groupby(daily.datetime.dt.year))
    columns = [f'IC_{a}' for a in ARMS] + list(CONTRASTS)
    intervals, support = {}, {}
    for length in [20, 40]:
        intervals[length], support[str(length)] = moving_block_intervals(daily[columns], length)
    rows = []
    for i, name in enumerate(CONTRASTS):
        a, b = hac_mean(daily[name], 20), hac_mean(daily[name], 40)
        row = dict(contrast=name, mean_delta=a['mean'], valid_dates=a['n'],
                   hac20_se=a['se'], hac20_p=a['p'] if eligible else np.nan,
                   hac40_se=b['se'], hac40_p=b['p'] if eligible else np.nan,
                   testable=bool(eligible and a['testable']),
                   reason=a['reason'] if eligible else 'annual_eligibility_failed')
        for length in [20, 40]:
            row[f'mbb{length}_lo'], row[f'mbb{length}_hi'] = intervals[length][:, 5 + i]
        rows.append(row)
    adjusted = holm_six([r['hac20_p'] for r in rows])
    for row, p in zip(rows, adjusted):
        row.update(holm_p=float(p), reject=bool(row['testable'] and p <= .05))
        row['decision'] = ('not_testable_no_rejection' if not row['testable'] else
                           'detected_positive_difference' if row['reject'] and row['mean_delta'] > 0 else
                           'detected_negative_difference' if row['reject'] else 'no_detected_difference')
    return pd.DataFrame(rows), support
