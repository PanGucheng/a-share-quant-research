"""Bounded canonical inputs. Role checks happen before any data I/O."""
from __future__ import annotations

import numpy as np
import pandas as pd

from factor_research.long_history_screening import (
    KEYS, LABEL, exact_primary_labels, frame_hash, normalize_keys,
)
from research_validation.canonical_dataset import read_effective_partition
from research_validation.research_protocol_v3 import START, END, allowed_dates


def read_features(partitions, factors, dates, *, access, protocol=None, fold_id=None, role=None):
    dates = pd.DatetimeIndex(dates)
    if protocol is not None:
        allowed_dates(protocol, fold_id, role, dates)
    if dates.empty or dates.has_duplicates or not dates.is_monotonic_increasing or dates.hasnans:
        raise ValueError('invalid feature dates')
    if dates.min() < START or dates.max() > END:
        raise ValueError('feature request outside development')
    names = list(factors)
    if not names or len(names) != len(set(names)) or set(names) & set(KEYS + [LABEL]):
        raise ValueError('invalid feature identity/order')
    pieces = {name: [] for name in names}
    for row in partitions.to_dict('records'):
        cols = [n for n in names if n in str(row['factors']).split(',')]
        selected = dates[(dates >= pd.Timestamp(row['effective_start'])) &
                         (dates <= pd.Timestamp(row['effective_end']))]
        if not cols or selected.empty:
            continue
        # Physical partition projection is bounded; expose only requested session keys.
        frame = normalize_keys(read_effective_partition(
            {**row, 'effective_start': selected.min(), 'effective_end': selected.max()}, columns=cols))
        frame = frame.loc[frame.datetime.isin(selected)].reset_index(drop=True)
        if frame.empty or not pd.DatetimeIndex(frame.datetime.unique()).equals(selected):
            raise ValueError('missing canonical sessions')
        access.append(dict(kind='feature', role=role or 'development_feature_audit',
                           fold_id=fold_id, columns=cols, start=str(selected.min()),
                           end=str(selected.max()), rows=len(frame), slice_hash=frame_hash(frame),
                           parent_sha256=row['output_sha256'], path=row['partition_path']))
        for col in cols:
            pieces[col].append(frame.set_index(KEYS)[col])
    axis, output = None, {}
    for name in names:
        if not pieces[name]:
            raise ValueError(f'missing feature partitions: {name}')
        value = pd.concat(pieces[name]).sort_index()
        if value.index.has_duplicates:
            raise ValueError('overlapping canonical keys')
        if axis is None:
            axis = value.index
        elif not value.index.equals(axis):
            raise ValueError('canonical feature key axes differ')
        output[name] = value.to_numpy(dtype='float64')
    frame = pd.DataFrame(output, index=axis).reset_index()
    if not pd.DatetimeIndex(frame.datetime.unique()).equals(dates):
        raise ValueError('missing feature dates')
    return frame


def read_keys(partitions, dates, *, access):
    """Use one factor's physical partitions, project only keys."""
    dates = pd.DatetimeIndex(dates)
    if dates.empty or dates.min() < START or dates.max() > END:
        raise ValueError('keys outside development')
    selected = partitions[partitions.factors.str.split(',').apply(lambda v: 'alpha158_BETA10' in v)]
    pieces = []
    for row in selected.to_dict('records'):
        days = dates[(dates >= pd.Timestamp(row['effective_start'])) & (dates <= pd.Timestamp(row['effective_end']))]
        if days.empty:
            continue
        frame = normalize_keys(read_effective_partition(
            {**row, 'effective_start': days.min(), 'effective_end': days.max()}, columns=[]))
        frame = frame.loc[frame.datetime.isin(days), KEYS]
        access.append(dict(kind='keys', start=str(days.min()), end=str(days.max()),
                           columns=KEYS, rows=len(frame), path=row['partition_path'], slice_hash=frame_hash(frame)))
        pieces.append(frame)
    if not pieces:
        raise ValueError('missing key partitions')
    result = normalize_keys(pd.concat(pieces))
    if not pd.DatetimeIndex(result.datetime.unique()).equals(dates):
        raise ValueError('incomplete key calendar')
    return result


def read_labels(keys, calendar, loader, *, access, protocol=None, fold_id=None, role=None):
    """Only maturity metadata is touched before the role check; no labels in prediction."""
    if role == 'predict':
        raise ValueError('prediction cannot read labels')
    keys = normalize_keys(keys)
    dates = pd.DatetimeIndex(keys.datetime.unique())
    if protocol is not None:
        allowed_dates(protocol, fold_id, role, dates)
        intervals = protocol['intervals'].set_index('feature_time').loc[dates]
        ceiling = (pd.Timestamp(protocol['folds'].set_index('fold_id').loc[fold_id, 'evaluation_start'])
                   - pd.Timedelta(days=1)) if role == 'train' else END
        if intervals.label_end_time.max() > ceiling:
            raise ValueError('label maturity exceeds role boundary')
    from research_validation.labels import build_label_date_map
    mapping = build_label_date_map(dates, calendar, entry_lag=1, holding_days=20)
    if mapping.exit_date.isna().any() or mapping.exit_date.max() > END:
        raise ValueError('unmatured label request')
    lo, hi = mapping.entry_date.min(), mapping.exit_date.max()
    symbols = sorted(keys.instrument.unique())
    prices = normalize_keys(loader(symbols, lo, hi))
    if prices.empty or not prices.datetime.between(lo, hi).all() or not set(prices.instrument) <= set(symbols):
        raise ValueError('price loader violated bounds')
    result = exact_primary_labels(keys, prices, calendar)
    result[LABEL] = result[LABEL].replace([np.inf, -np.inf], np.nan)
    access.append(dict(kind='price', role=role or 'maturity_count_audit', fold_id=fold_id,
                       start=str(lo), end=str(hi), rows=len(prices), columns=['$close'],
                       slice_hash=frame_hash(prices), label_hash=frame_hash(result)))
    return result[[*KEYS, LABEL, 'exit_date']]


def feature_profile(frame, factors):
    rows = []
    for name in factors:
        values = frame[name].to_numpy(dtype='float64')
        finite = np.isfinite(values)
        rows.append(dict(factor=name, rows=len(values), finite_samples=int(finite.sum()),
                         finite_dates=int(frame.loc[finite, 'datetime'].nunique()),
                         infinite_samples=int(np.isinf(values).sum()),
                         minimum=float(values[finite].min()) if finite.any() else np.nan,
                         maximum=float(values[finite].max()) if finite.any() else np.nan))
    return pd.DataFrame(rows)


def combine_profiles(profiles):
    merged = pd.concat(profiles).groupby('factor', sort=True).agg(
        rows=('rows', 'sum'), finite_samples=('finite_samples', 'sum'),
        finite_dates=('finite_dates', 'sum'), infinite_samples=('infinite_samples', 'sum'),
        minimum=('minimum', 'min'), maximum=('maximum', 'max')).reset_index()
    merged['finite_fraction'] = merged.finite_samples / merged.rows
    merged['eligible'] = (merged.finite_dates >= 2) & (merged.minimum < merged.maximum)
    merged['reason'] = np.select([merged.finite_samples == 0, merged.finite_dates < 2,
                                 merged.minimum == merged.maximum],
                                ['all_missing', 'fewer_than_two_finite_dates', 'constant'], default='eligible')
    return merged
