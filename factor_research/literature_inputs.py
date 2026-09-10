"""D1 feature-only I/O. No label, prediction, training or evaluation imports."""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from factor_research.literature_representation import KEYS, digest, legal_dates
from research_validation.canonical_dataset import read_effective_partition


def frame_digest(frame):
    h = hashlib.sha256(digest(list(frame.columns)).encode())
    h.update(pd.util.hash_pandas_object(frame, index=False).to_numpy().tobytes())
    return h.hexdigest()


def read_features(partitions, factors, dates, *, approved, access):
    days = legal_dates(dates)  # Must precede even partition selection and metadata path access.
    names = list(factors)
    if not names or len(names) != len(set(names)) or not set(names) <= set(approved) or set(names) & set(KEYS):
        raise ValueError('unapproved D1 feature projection')
    pieces = {name: [] for name in names}
    for row in partitions.to_dict('records'):
        cols = [name for name in names if name in str(row['factors']).split(',')]
        selected = days[(days >= pd.Timestamp(row['effective_start'])) & (days <= pd.Timestamp(row['effective_end']))]
        if not cols or selected.empty:
            continue
        event = dict(kind='canonical_feature_slice', columns=cols, start=str(selected.min().date()),
                     end=str(selected.max().date()), path=row['partition_path'],
                     parent_hash_metadata_only=row['output_sha256'])
        access({**event, 'stage': 'request'})
        frame = read_effective_partition({**row, 'effective_start': selected.min(),
                                          'effective_end': selected.max()}, columns=cols)
        if not frame.datetime.between(selected.min(), selected.max()).all():
            raise ValueError('reader returned dates outside approved bounds')
        frame = frame.loc[frame.datetime.isin(selected), KEYS + cols].reset_index(drop=True)
        if frame.empty or frame.duplicated(KEYS).any() or frame.instrument.isna().any():
            raise ValueError('missing or duplicate canonical keys')
        if not pd.DatetimeIndex(frame.datetime.unique()).equals(selected):
            raise ValueError('missing canonical sessions')
        access({**event, 'stage': 'complete', 'rows': len(frame), 'slice_hash': frame_digest(frame)})
        indexed = frame.set_index(KEYS)
        for col in cols:
            pieces[col].append(indexed[col].copy())
    axis, output = None, {}
    for name in names:
        if not pieces[name]:
            raise ValueError(f'missing parent: {name}')
        value = pd.concat(pieces[name]).sort_index()
        if value.index.has_duplicates:
            raise ValueError('overlapping canonical keys')
        if axis is None:
            axis = value.index
        elif not value.index.equals(axis):
            raise ValueError('canonical feature key axes differ')
        output[name] = value.to_numpy(dtype=np.float64)
    result = pd.DataFrame(output, index=axis).reset_index()
    if not pd.DatetimeIndex(result.datetime.unique()).equals(days):
        raise ValueError('incomplete requested calendar')
    return result


def check_aliases(frame, inventory):
    checked = 0
    for row in inventory:
        if row['factor'] != row['exact_alias']:
            a, b = frame[row['factor']].to_numpy(), frame[row['exact_alias']].to_numpy()
            if not np.array_equal(a, b, equal_nan=True):
                raise ValueError(f"registered exact alias no longer equal: {row['factor']}")
            checked += 1
    return checked
