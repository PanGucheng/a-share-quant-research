"""Fixed-model train/predict primitives: evaluation labels are never an argument to fit."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import time

import lightgbm as lgb
import numpy as np
import pandas as pd

from factor_research.long_history_screening import KEYS, LABEL, normalize_keys
from model_research.preprocessing import daily_equal_weights
from model_research.targets import daily_cross_sectional_rank_centered
from research_validation.canonical_dataset import canonical_hash
from research_validation.research_protocol_v3 import allowed_dates


def prepare_training_batch(features, labels, factors, *, protocol, fold_id, minimum_pairs=100):
    features, labels = normalize_keys(features), normalize_keys(labels)
    days = pd.DatetimeIndex(features.datetime.unique())
    allowed_dates(protocol, fold_id, 'train', days)
    if list(features.columns) != [*KEYS, *factors]:
        raise ValueError('feature order/schema mismatch')
    if not features[KEYS].equals(labels[KEYS]):
        raise ValueError('training feature/label key axes differ')
    intervals = protocol['intervals'].set_index('feature_time')
    expected_ends = labels.datetime.map(intervals.label_end_time)
    if not pd.to_datetime(labels.exit_date).equals(expected_ends):
        raise ValueError('label interval mismatch')
    finite_labels = labels.copy()
    finite_labels[LABEL] = finite_labels[LABEL].replace([np.inf, -np.inf], np.nan)
    # Rank over the same label universe BEFORE any pool-dependent feature mask.
    target, _ = daily_cross_sectional_rank_centered(
        finite_labels, label_column=LABEL, minimum_daily_pairs=minimum_pairs)
    matrix = features[factors].to_numpy(dtype='float64', copy=True)
    matrix[~np.isfinite(matrix)] = np.nan
    mask = target.notna().to_numpy() & np.isfinite(matrix).any(axis=1)
    count = features.loc[mask].groupby('datetime').size().reindex(days, fill_value=0)
    if count.lt(minimum_pairs).any():
        raise ValueError('insufficient daily training pairs after feature mask')
    selected = features.loc[mask, KEYS]
    return (matrix[mask], target.to_numpy()[mask], daily_equal_weights(selected.datetime.to_numpy()),
            {'input_rows': len(features), 'fit_rows': int(mask.sum()),
             'min_daily_fit_pairs': int(count.min()),
             'fit_keys_hash': hashlib.sha256(pd.util.hash_pandas_object(selected, index=False).values.tobytes()).hexdigest()})


@dataclass
class FrozenAnnualModel:
    booster: object
    factors: tuple[str, ...]
    fold_id: str
    receipt: dict


def fit_arrays(matrix, target, weights, factors, *, fold_id, config):
    if config['early_stopping'] is not False or config['competition_authorized'] is not False:
        raise ValueError('P2 fixed-model contract required')
    if lgb.__version__ != config['lightgbm_version']:
        raise ValueError('LightGBM version differs from frozen configuration')
    if len(factors) == 0 or len(set(factors)) != len(factors) or matrix.shape != (len(target), len(factors)):
        raise ValueError('invalid training matrix/feature identity')
    if len(target) == 0 or not np.isfinite(target).all() or not np.isfinite(weights).all() or (weights <= 0).any():
        raise ValueError('invalid target/weights')
    if np.isinf(matrix).any() or np.isnan(matrix).all(axis=0).any() or np.isnan(matrix).all(axis=1).any():
        raise ValueError('invalid all-empty training rows/columns or infinity')
    tick = time.perf_counter()
    dataset = lgb.Dataset(matrix, label=target, weight=weights, feature_name=list(factors),
                          params=config['model_params'], free_raw_data=False)
    dataset.construct()
    construct_seconds = time.perf_counter() - tick
    tick = time.perf_counter()
    booster = lgb.train(config['model_params'], dataset, num_boost_round=config['num_boost_round'])
    seconds = time.perf_counter() - tick
    model_string = booster.model_to_string()
    receipt = dict(model_id=config['model_id'], fold_id=fold_id,
                   config_hash=canonical_hash(config), ordered_features=list(factors),
                   fit_rows=len(target), dataset_seconds=construct_seconds, fit_seconds=seconds,
                   model_sha256=hashlib.sha256(model_string.encode()).hexdigest(),
                   actual_iterations=booster.current_iteration(),
                   requested_iterations=config['num_boost_round'],
                   outer_labels_accessed=False, early_stopping=False,
                   lightgbm_version=lgb.__version__)
    # Serialized model includes the library's fully resolved parameter block.
    return FrozenAnnualModel(booster, tuple(factors), fold_id, receipt)


def predict(model, features, *, protocol):
    if list(features.columns) != [*KEYS, *model.factors]:
        raise ValueError('prediction feature order/schema mismatch')
    features = normalize_keys(features)
    allowed_dates(protocol, model.fold_id, 'predict', pd.DatetimeIndex(features.datetime.unique()))
    matrix = features[list(model.factors)].to_numpy(dtype='float64', copy=True)
    matrix[~np.isfinite(matrix)] = np.nan
    valid = np.isfinite(matrix).any(axis=1)
    if not features.loc[valid].datetime.nunique() == features.datetime.nunique():
        raise ValueError('entire prediction session has no usable features')
    scores = np.full(len(features), np.nan)
    scores[valid] = model.booster.predict(matrix[valid], num_threads=8)
    if not np.isfinite(scores[valid]).all():
        raise ValueError('model generated nonfinite predictions')
    return features[KEYS].assign(score=scores, reason=np.where(valid, 'predicted', 'all_features_missing'))
