"""Calendar authority for V3; no feature, price, or model access."""
from __future__ import annotations

import pandas as pd

from research_validation.purged_split import label_intervals

START = pd.Timestamp('2010-01-29')
END = pd.Timestamp('2023-12-29')
PHYSICAL_END = pd.Timestamp('2026-06-09')
DATASET_ID = 'canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423'


def validate_calendar(calendar):
    dates = pd.DatetimeIndex(calendar)
    if dates.hasnans or dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError('calendar must be ordered, unique and non-null')
    if not dates.equals(dates.normalize()):
        raise ValueError('calendar must contain normalized sessions')
    dates = dates[(dates >= START) & (dates <= PHYSICAL_END)]
    if dates.empty or dates[0] != START or dates[-1] != PHYSICAL_END or END not in dates:
        raise ValueError('incomplete canonical calendar boundaries')
    return dates


def build_protocol(calendar):
    dates = validate_calendar(calendar)
    intervals = label_intervals(dates, horizon=20, execution_lag=1)
    folds, assignments, purged = [], [], []
    for year in range(2015, 2024):
        evaluation = dates[dates.year == year]
        if len(evaluation) < 200:
            raise ValueError('incomplete annual calendar')
        train = intervals.loc[(intervals.feature_time < evaluation[0]) &
                              (intervals.label_end_time < evaluation[0])]
        excluded = intervals.loc[(intervals.feature_time < evaluation[0]) &
                                 (intervals.label_end_time >= evaluation[0])]
        scored = intervals.loc[intervals.feature_time.isin(evaluation) &
                               (intervals.label_end_time <= END)]
        if train.empty or scored.empty:
            raise ValueError('empty training or mature evaluation dates')
        fold_id = f'annual_{year}'
        folds.append(dict(fold_id=fold_id, train_start=train.feature_time.min(),
                          last_legal_train_signal=train.feature_time.max(),
                          train_label_end=train.label_end_time.max(),
                          evaluation_start=evaluation[0], evaluation_end=evaluation[-1],
                          latest_mature_eval_signal=scored.feature_time.max(),
                          label_end=scored.label_end_time.max(), train_dates=len(train),
                          nominal_dates=len(evaluation), usable_dates=len(scored),
                          purged_dates=len(excluded), extra_embargo=0))
        for role, values in [('train', train.feature_time), ('predict', evaluation),
                             ('evaluate', scored.feature_time)]:
            assignments.extend(dict(fold_id=fold_id, role=role, datetime=d) for d in values)
        purged.extend(dict(fold_id=fold_id, **r) for r in excluded.to_dict('records'))
    return {'folds': pd.DataFrame(folds), 'assignments': pd.DataFrame(assignments),
            'purged': pd.DataFrame(purged), 'intervals': intervals}


def allowed_dates(protocol, fold_id, role, requested):
    if role not in {'train', 'predict', 'evaluate'}:
        raise ValueError('unknown data role')
    dates = pd.DatetimeIndex(requested)
    if dates.empty or dates.hasnans or dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError('requested dates must be nonempty, ordered and unique')
    source = protocol['assignments']
    legal = source.loc[(source.fold_id == fold_id) & (source.role == role), 'datetime']
    if not dates.isin(legal).all() or dates.min() < START or dates.max() > END:
        raise ValueError('dates outside fold role or development boundary')
    return dates


def training_dates(protocol, fold_id, history='expanding'):
    source = protocol['assignments']
    dates = pd.DatetimeIndex(source.loc[(source.fold_id == fold_id) & (source.role == 'train'), 'datetime'])
    if history == 'sliding_4_calendar_years':
        year = int(fold_id.removeprefix('annual_'))
        dates = dates[dates >= pd.Timestamp(year - 4, 1, 1)]
    elif history != 'expanding':
        raise ValueError('unregistered training history')
    return allowed_dates(protocol, fold_id, 'train', dates)
