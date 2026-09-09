"""Fixed-model train/predict primitives: evaluation labels are never an argument to fit."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
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
    if matrix.dtype != np.float64:
        raise ValueError('V3 requires float64 feature input; lossy casts are not qualified')
    return _fit_data(matrix, [matrix], target, weights, factors, fold_id=fold_id, config=config)


class Float64FileSequence(lgb.Sequence):
    """Read bounded rows from a closed, immutable raw float64 block without mmap."""

    batch_size = 4096

    def __init__(self, path, columns):
        self.path, self.columns = Path(path), columns
        size = self.path.stat().st_size
        if columns <= 0 or size == 0 or size % (8 * columns):
            raise ValueError('invalid float64 block dimensions')
        self.rows = size // (8 * columns)
        self.handle = self.path.open('rb')

    def __len__(self):
        return self.rows

    def __getitem__(self, index):
        scalar = isinstance(index, (int, np.integer))
        if scalar:
            start, stop = int(index), int(index) + 1
        elif isinstance(index, slice) and index.step in (None, 1):
            start, stop, _ = index.indices(self.rows)
        else:
            raise TypeError('only integer or contiguous slice supported')
        if not 0 <= start < stop <= self.rows:
            raise IndexError('float64 block row outside bounds')
        self.handle.seek(start * self.columns * 8)
        result = np.fromfile(self.handle, dtype=np.float64, count=(stop - start) * self.columns)
        if result.size != (stop - start) * self.columns:
            raise ValueError('truncated float64 block')
        result = result.reshape(stop - start, self.columns)
        return result[0] if scalar else result

    def close(self):
        self.handle.close()


def fit_sequences(sequences, target, weights, factors, *, fold_id, config):
    if not sequences or sum(map(len, sequences)) != len(target):
        raise ValueError('invalid sequence row count')
    return _fit_data(sequences, sequences, target, weights, factors, fold_id=fold_id, config=config)


def _fit_data(data, blocks, target, weights, factors, *, fold_id, config):
    if config['early_stopping'] is not False or config['competition_authorized'] is not False:
        raise ValueError('P2 fixed-model contract required')
    if lgb.__version__ != config['lightgbm_version']:
        raise ValueError('LightGBM version differs from frozen configuration')
    if (len(factors) == 0 or len(set(factors)) != len(factors)
            or len(weights) != len(target) or target.ndim != 1 or weights.ndim != 1):
        raise ValueError('invalid training matrix/feature identity')
    if len(target) == 0 or not np.isfinite(target).all() or not np.isfinite(weights).all() or (weights <= 0).any():
        raise ValueError('invalid target/weights')
    finite_columns = np.zeros(len(factors), dtype=bool)
    rows = 0
    for block in blocks:
        for start in range(0, len(block), 4096):
            batch = block[start:min(start + 4096, len(block))]
            if batch.ndim != 2 or batch.shape[1] != len(factors) or batch.dtype != np.float64:
                raise ValueError('invalid float64 feature shape')
            finite = np.isfinite(batch)
            if np.isinf(batch).any() or not finite.any(axis=1).all():
                raise ValueError('invalid all-empty training rows/columns or infinity')
            finite_columns |= finite.any(axis=0)
            rows += len(batch)
    if rows != len(target) or not finite_columns.all():
        raise ValueError('invalid row count or empty training columns')
    tick = time.perf_counter()
    dataset = lgb.Dataset(data, label=target, weight=weights, feature_name=list(factors),
                          params=config['model_params'], free_raw_data=True)
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
