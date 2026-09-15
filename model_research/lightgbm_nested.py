"""Past-only selection policy; no filesystem, outer outcomes or portfolio inputs."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import rankdata

TRIALS = [
    ('fixed100', {}), ('base_es', {}), ('lr06', {'learning_rate': .06}),
    ('leaves31', {'num_leaves': 31, 'max_depth': 5}),
    ('leaves63', {'num_leaves': 63, 'max_depth': 6}),
    ('min300', {'min_data_in_leaf': 300}), ('l1_1', {'lambda_l1': 1.}),
    ('l2_10', {'lambda_l2': 10.}), ('ff100', {'feature_fraction': 1.}),
]
MAX_ROUNDS = 800
PATIENCE = 50
PLATEAU_TOLERANCE = .001


def inner_split(protocol, fold):
    from research_validation.research_protocol_v3 import training_dates
    outer = training_dates(protocol, fold)
    valid = outer[outer.year == int(fold[-4:]) - 1]
    if valid.empty:
        raise ValueError('empty inner validation')
    intervals = protocol['intervals'].set_index('feature_time')
    train = outer[(outer < valid[0]) & (intervals.loc[outer, 'label_end_time'].to_numpy() < valid[0])]
    boundary = pd.Timestamp(protocol['folds'].set_index('fold_id').loc[fold, 'evaluation_start'])
    if (train.empty or train.intersection(valid).size or len(valid) < 100
            or intervals.loc[train, 'label_end_time'].max() >= valid[0]
            or intervals.loc[valid, 'label_end_time'].max() >= boundary):
        raise ValueError('inner maturity/temporal isolation failure')
    return train, valid


def daily_ic(prediction, target, counts):
    """Finite fixed sample, average ties; constant early-stop days score zero."""
    x, y = np.asarray(prediction), np.asarray(target)
    counts = np.asarray(counts, dtype=int)
    if (x.ndim != 1 or x.shape != y.shape or counts.sum() != len(x)
            or (counts < 2).any() or not np.isfinite(x).all() or not np.isfinite(y).all()):
        raise ValueError('invalid fixed daily metric sample')
    results, constants, offset = [], 0, 0
    for n in counts:
        a, b = rankdata(x[offset:offset+n]), rankdata(y[offset:offset+n])
        a, b = a-a.mean(), b-b.mean()
        scale = np.linalg.norm(a) * np.linalg.norm(b)
        constants += int(scale == 0)
        results.append(float(np.clip(a @ b / scale, -1, 1)) if scale else 0.)
        offset += n
    return np.array(results), constants


def select_trial(rows):
    if [r['trial'] for r in rows] != [t[0] for t in TRIALS]:
        raise ValueError('all predefined trials required in order')
    if any(not np.isfinite(r['mean_ic']) or not 1 <= r['rounds'] <= MAX_ROUNDS for r in rows):
        raise ValueError('invalid trial result')
    best = max(r['mean_ic'] for r in rows)
    plateau = [r for r in rows if r['mean_ic'] >= best - PLATEAU_TOLERANCE]
    selected = min(plateau, key=lambda r: (r['leaves']*r['rounds'], r['leaves'], r['rounds'], rows.index(r)))
    return dict(selected=selected['trial'], rounds=selected['rounds'],
                inner_best_mean=best, plateau=[r['trial'] for r in plateau],
                outer_outcomes_used=False)


def describe(values):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if not len(x):
        return dict(mean_ic=None, icir=None, dates=0)
    std = x.std(ddof=1) if len(x) > 1 else 0.
    return dict(mean_ic=float(x.mean()), icir=float(x.mean()/std) if std > 0 else None, dates=len(x))
