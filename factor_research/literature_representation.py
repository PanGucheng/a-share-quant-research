"""Outcome-free representation recipes and daily float64 transforms.

No filesystem reads, labels, model imports, or fitted state in this module.
"""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np
import pandas as pd

START, END = pd.Timestamp('2010-01-29'), pd.Timestamp('2023-12-29')
KEYS = ['datetime', 'instrument']


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def legal_dates(dates):
    days = pd.DatetimeIndex(dates)
    if (days.empty or days.hasnans or days.has_duplicates or not days.is_monotonic_increasing
            or days.tz is not None or not days.equals(days.normalize())
            or days.min() < START or days.max() > END):
        raise ValueError('D1 dates must be sorted, unique, nonempty and within development')
    return days


def bucket(lag):
    if not isinstance(lag, int) or not 0 <= lag <= 63:
        raise ValueError('invalid dense lag')
    return 'd0' if lag == 0 else 'd1_5' if lag <= 5 else 'd6_21' if lag <= 21 else 'd22_63'


def grid_center(lags):
    values = sorted(set(lags))
    if not values:
        raise ValueError('empty lag grid')
    for lag in values:
        bucket(lag)
    return values[(len(values) - 1) // 2]


def validate_recipe(recipe):
    if (recipe['scope'] != 'D1_feature_only_candidate' or recipe['d2_authorized'] is not False
            or recipe.get('outcomes_authorized', False) is not False
            or recipe.get('recent_authorized', False) is not False):
        raise ValueError('D1 candidate scope required')
    names = recipe['parents']
    if not names or len(names) != len(set(names)) or set(names) & set(KEYS):
        raise ValueError('invalid parent identity')
    policy = recipe['diagnostic_policy']
    if (type(policy['rank_min']) is not int or policy['rank_min'] < 2
            or not 0 < policy['child_fraction'] <= 1):
        raise ValueError('invalid diagnostic policy')
    outputs = set(names)
    seen_parents = set()
    for node in recipe['composites']:
        if node['id'] in outputs or not node['families']:
            raise ValueError('duplicate output or empty composite')
        outputs.add(node['id'])
        family_ids = set()
        for family in node['families']:
            if family['id'] in family_ids or not family['members']:
                raise ValueError('duplicate/empty family')
            family_ids.add(family['id'])
            for leaf in family['members']:
                name = leaf['factor']
                if name not in names or name in seen_parents or leaf['sign'] not in (-1, 1):
                    raise ValueError('invalid, duplicate or unsigned composite dependency')
                seen_parents.add(name)
    u, r = recipe['u'], recipe['representatives']
    if set(u) & seen_parents or set(u) & set(r):
        raise ValueError('raw carry-through overlaps compressible group')
    if not set(u + r) <= set(names) or len(u + r) != len(set(u + r)):
        raise ValueError('invalid raw columns')
    c = [n['id'] for n in recipe['composites']]
    expected = {'R': sorted(u + r), 'C': sorted(u + c), 'H': sorted(u + r + c)}
    if recipe['arms'] != expected:
        raise ValueError('arm composition/order mismatch')
    if set(names) != set(u) | seen_parents:
        raise ValueError('parent identity has no disposition')


def rank_column(values, minimum):
    x = np.asarray(values, dtype=np.float64)
    finite = np.isfinite(x)
    n = int(finite.sum())
    out = np.full(len(x), np.nan)
    reason = 'all_missing' if n == 0 else 'constant' if np.unique(x[finite]).size <= 1 else 'below_rank_min' if n < minimum else 'valid'
    if reason == 'valid':
        out[finite] = (pd.Series(x[finite]).rank(method='average').to_numpy() - .5) / n - .5
    return out, {'finite_n': n, 'unique_n': int(np.unique(x[finite]).size),
                 'n_below_100': n < 100, 'rank_reason': reason, 'infinite_n': int(np.isinf(x).sum())}


def average_children(children, fraction):
    values = np.column_stack(children)
    count = np.isfinite(values).sum(axis=1)
    needed = math.ceil(fraction * values.shape[1])
    out = np.full(len(values), np.nan)
    valid = count >= needed
    out[valid] = np.nansum(values[valid], axis=1) / count[valid]
    return out, count, needed


def transform_day(frame, recipe):
    """Complete dated universe is ranked before any outcome-dependent mask."""
    validate_recipe(recipe)
    if list(frame.columns) != KEYS + recipe['parents']:
        raise ValueError('only ordered keys and approved feature parents are accepted')
    days = pd.DatetimeIndex(pd.to_datetime(frame.datetime).unique())
    legal_dates(days)
    if len(days) != 1 or frame.duplicated(KEYS).any() or frame.instrument.isna().any():
        raise ValueError('one complete date with unique keys required')
    for col in recipe['parents']:
        if frame[col].dtype != np.float64:
            raise ValueError('D1 requires float64 values')
    policy = recipe['diagnostic_policy']
    rank, leaf_rows, family_rows, output_rows = {}, [], [], []
    for name in recipe['parents']:
        if name in recipe['u']:
            x = frame[name].to_numpy()
            finite = np.isfinite(x)
            stats = dict(finite_n=int(finite.sum()), unique_n=int(np.unique(x[finite]).size),
                         n_below_100=int(finite.sum()) < 100, rank_reason='raw_U_not_ranked',
                         infinite_n=int(np.isinf(x).sum()))
        else:
            rank[name], stats = rank_column(frame[name], policy['rank_min'])
        leaf_rows.append(dict(factor=name, universe_n=len(frame), **stats))
    generated = {name: frame[name].where(np.isfinite(frame[name])).to_numpy() for name in recipe['parents']}
    for node in recipe['composites']:
        families = []
        for family in node['families']:
            a, counts, needed = average_children(
                [rank[x['factor']] * x['sign'] for x in family['members']], policy['child_fraction'])
            families.append(a)
            family_rows.append(dict(output=node['id'], family=family['id'],
                frozen_nodes=len(family['members']), needed_nodes=needed, universe_n=len(frame),
                valid_rows=int(np.isfinite(a).sum()), min_nodes=int(counts.min()),
                mean_nodes=float(counts.mean()), max_nodes=int(counts.max()),
                node_count_histogram=json.dumps({str(k):int(v) for k,v in zip(*np.unique(counts, return_counts=True))})))
        c, counts, needed = average_children(families, policy['child_fraction'])
        generated[node['id']] = c
        valid = np.isfinite(c)
        full = len(families)
        raw_available = np.column_stack([np.isfinite(frame[m['factor']])
            for f in node['families'] for m in f['members']]).any(axis=1)
        output_rows.append(dict(output=node['id'], frozen_families=full, needed_families=needed,
            universe_n=len(frame), valid_rows=int(valid.sum()), missing_rows=int((~valid).sum()),
            single_family_valid_rows=int(((counts == 1) & valid).sum()),
            effective_family_sum=int(counts[valid].sum()),
            raw_any_parent_rows=int(raw_available.sum()),
            raw_available_but_output_missing=int((raw_available & ~valid).sum()),
            output_n_below_100=int(valid.sum()) < 100,
            family_count_histogram=json.dumps({str(k):int(v) for k,v in zip(*np.unique(counts, return_counts=True))}),
            max_family_weight=float((1 / counts[valid]).max()) if valid.any() else None,
            mean_l1_weight_drift=float((2 * (full - counts[valid]) / full).mean()) if valid.any() else None,
            constant_output=bool(valid.any() and np.unique(c[valid]).size == 1),
            infinite_n=int(np.isinf(c).sum())))
    for rows in [leaf_rows, family_rows, output_rows]:
        for row in rows:
            row['datetime'] = days[0].strftime('%Y-%m-%d')
    # Build once, then select arms; never expose unrelated columns to a model.
    result = pd.concat([frame[KEYS].reset_index(drop=True), pd.DataFrame(generated)], axis=1)
    arms = {arm: result[KEYS + columns].copy() for arm, columns in recipe['arms'].items()}
    return arms, {'leaves': leaf_rows, 'families': family_rows, 'outputs': output_rows}
