from __future__ import annotations

from dataclasses import dataclass

import numpy as np


WEIGHTED_MEDIAN_ALGORITHM = "stable_weighted_median_v1"
NEAR_ZERO_VARIANCE_THRESHOLD = 1e-12


def daily_equal_weights(dates: np.ndarray) -> np.ndarray:
    values = np.asarray(dates)
    unique, inverse, counts = np.unique(values, return_inverse=True, return_counts=True)
    del unique
    return 1.0 / counts[inverse].astype(float)


def stable_weighted_median(
    values: np.ndarray,
    weights: np.ndarray,
    *,
    canonical_keys: np.ndarray | None = None,
) -> float:
    value_array = np.asarray(values, dtype=float)
    weight_array = np.asarray(weights, dtype=float)
    if value_array.shape != weight_array.shape:
        raise ValueError("values and weights must have identical shape")
    valid = np.isfinite(value_array) & np.isfinite(weight_array) & (weight_array > 0)
    if not valid.any():
        raise ValueError("weighted median has no finite positively weighted observations")
    values_valid = value_array[valid]
    weights_valid = weight_array[valid]
    if canonical_keys is not None:
        keys = np.asarray(canonical_keys)
        if keys.shape != value_array.shape:
            raise ValueError("canonical_keys must have identical shape")
    # The returned statistic is a value, so reordering observations tied on that
    # value cannot change the weighted-median value even when their weights differ.
    # A stable numeric sort is therefore exactly equivalent to lexsorting large
    # canonical string keys, while avoiding the dominant conversion/comparison cost.
    order = np.argsort(values_valid, kind="stable")
    ordered_values = values_valid[order]
    ordered_weights = weights_valid[order]
    cutoff = ordered_weights.sum() / 2.0
    index = int(np.searchsorted(np.cumsum(ordered_weights), cutoff, side="left"))
    return float(ordered_values[index])


@dataclass(frozen=True)
class WeightedPreprocessingFit:
    feature_names: tuple[str, ...]
    medians: np.ndarray
    means: np.ndarray
    variances: np.ndarray

    def transform(self, values: np.ndarray) -> np.ndarray:
        matrix = np.asarray(values, dtype=float)
        if matrix.ndim != 2 or matrix.shape[1] != len(self.feature_names):
            raise ValueError("feature count/order does not match frozen preprocessing")
        result = matrix.copy()
        result[~np.isfinite(result)] = np.nan
        all_missing = np.isnan(result).all(axis=1)
        if all_missing.any():
            raise ValueError("all-NaN rows must be excluded before transform")
        for index in range(result.shape[1]):
            missing = np.isnan(result[:, index])
            result[missing, index] = self.medians[index]
        return (result - self.means) / np.sqrt(self.variances)


def fit_weighted_preprocessing(
    values: np.ndarray,
    sample_weights: np.ndarray,
    *,
    feature_names: tuple[str, ...],
    canonical_row_keys: np.ndarray,
) -> WeightedPreprocessingFit:
    matrix = np.asarray(values, dtype=float).copy()
    matrix[~np.isfinite(matrix)] = np.nan
    weights = np.asarray(sample_weights, dtype=float)
    if matrix.ndim != 2:
        raise ValueError("values must be a 2D matrix")
    if matrix.shape[1] != len(feature_names):
        raise ValueError("feature_names must match matrix width")
    if matrix.shape[0] != len(weights):
        raise ValueError("sample_weights must match matrix rows")
    if np.isnan(matrix).all(axis=1).any():
        raise ValueError("all-NaN rows must be excluded consistently across models")
    if np.isnan(matrix).all(axis=0).any():
        missing = [
            feature_names[index]
            for index in np.flatnonzero(np.isnan(matrix).all(axis=0))
        ]
        raise ValueError(f"training features entirely NaN: {missing}")

    medians = np.asarray(
        [
            stable_weighted_median(
                matrix[:, index],
                weights,
                canonical_keys=canonical_row_keys,
            )
            for index in range(matrix.shape[1])
        ],
        dtype=float,
    )
    imputed = matrix.copy()
    for index in range(imputed.shape[1]):
        missing = np.isnan(imputed[:, index])
        imputed[missing, index] = medians[index]
    total_weight = float(weights.sum())
    means = np.sum(imputed * weights[:, None], axis=0) / total_weight
    variances = (
        np.sum(((imputed - means) ** 2) * weights[:, None], axis=0) / total_weight
    )
    if (variances <= NEAR_ZERO_VARIANCE_THRESHOLD).any():
        blocked = [
            feature_names[index]
            for index in np.flatnonzero(
                variances <= NEAR_ZERO_VARIANCE_THRESHOLD
            )
        ]
        raise ValueError(f"near-zero weighted variance features: {blocked}")
    return WeightedPreprocessingFit(
        feature_names=feature_names,
        medians=medians,
        means=means,
        variances=variances,
    )
