from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from model_research.development_dry_run import _fit_from_spool
from model_research.linear_models import _validation_metrics
from model_research.preprocessing import (
    NEAR_ZERO_VARIANCE_THRESHOLD,
    WeightedPreprocessingFit,
    stable_weighted_median,
)
from model_research.runtime_timing import RuntimeTimingRecorder


def _legacy_fit_from_spool(
    spool_paths: list[Path], factors: list[str]
) -> WeightedPreprocessingFit:
    medians: list[float] = []
    for factor in factors:
        values: list[np.ndarray] = []
        weights: list[np.ndarray] = []
        keys: list[np.ndarray] = []
        for path in spool_paths:
            frame = pd.read_parquet(
                path,
                columns=["datetime", "instrument", "__weight", factor],
            )
            values.append(frame[factor].to_numpy(dtype=float))
            weights.append(frame["__weight"].to_numpy(dtype=float))
            keys.append(
                (
                    frame["datetime"].astype(str)
                    + "|"
                    + frame["instrument"].astype(str)
                ).to_numpy()
            )
        medians.append(
            stable_weighted_median(
                np.concatenate(values),
                np.concatenate(weights),
                canonical_keys=np.concatenate(keys),
            )
        )
    median_array = np.asarray(medians, dtype=float)
    weighted_sum = np.zeros(len(factors), dtype=float)
    weighted_square_sum = np.zeros(len(factors), dtype=float)
    total_weight = 0.0
    for path in spool_paths:
        frame = pd.read_parquet(path, columns=["__weight", *factors])
        weights = frame["__weight"].to_numpy(dtype=float)
        matrix = frame[factors].to_numpy(dtype=float)
        matrix[~np.isfinite(matrix)] = np.nan
        for index in range(matrix.shape[1]):
            missing = np.isnan(matrix[:, index])
            matrix[missing, index] = median_array[index]
        weighted_sum += np.sum(matrix * weights[:, None], axis=0)
        weighted_square_sum += np.sum((matrix**2) * weights[:, None], axis=0)
        total_weight += float(weights.sum())
    means = weighted_sum / total_weight
    variances = weighted_square_sum / total_weight - means**2
    assert (variances > NEAR_ZERO_VARIANCE_THRESHOLD).all()
    return WeightedPreprocessingFit(
        feature_names=tuple(factors),
        medians=median_array,
        means=means,
        variances=variances,
    )


def _write_spools(tmp_path: Path) -> tuple[list[Path], list[str]]:
    rng = np.random.default_rng(20260815)
    factors = [f"factor_{index:03d}" for index in range(11)]
    paths: list[Path] = []
    for batch in range(3):
        row_count = 37 + batch * 5
        values = rng.normal(size=(row_count, len(factors)))
        values[::7, batch] = np.nan
        values[::11, (batch + 3) % len(factors)] = np.inf
        frame = pd.DataFrame(values, columns=factors)
        frame.insert(
            0,
            "instrument",
            [f"{600000 + index:06d}.SH" for index in range(row_count)],
        )
        frame.insert(
            0,
            "datetime",
            pd.Timestamp("2024-01-02") + pd.to_timedelta(batch, unit="D"),
        )
        frame["__weight"] = 1.0 / row_count
        path = tmp_path / f"spool_{batch}.parquet"
        frame.to_parquet(path, index=False)
        paths.append(path)
    return paths, factors


def test_batched_spool_preprocessing_matches_legacy_exactly(tmp_path: Path) -> None:
    paths, factors = _write_spools(tmp_path)
    legacy = _legacy_fit_from_spool(paths, factors)
    batched = _fit_from_spool(paths, factors, factor_batch_size=3)

    assert batched.feature_names == legacy.feature_names
    np.testing.assert_array_equal(batched.medians, legacy.medians)
    np.testing.assert_array_equal(batched.means, legacy.means)
    np.testing.assert_allclose(batched.variances, legacy.variances, rtol=2e-15, atol=0)


def test_numeric_weighted_median_sort_matches_legacy_key_lexsort() -> None:
    rng = np.random.default_rng(20260817)
    values = rng.integers(-5, 6, size=20_000).astype(float)
    weights = rng.uniform(0.01, 2.0, size=len(values))
    keys = np.asarray([f"row_{index:06d}" for index in rng.permutation(len(values))])
    valid = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    legacy_order = np.lexsort((keys[valid].astype(str), values[valid]))
    legacy_values = values[valid][legacy_order]
    legacy_weights = weights[valid][legacy_order]
    legacy_index = int(
        np.searchsorted(
            np.cumsum(legacy_weights), legacy_weights.sum() / 2.0, side="left"
        )
    )

    assert stable_weighted_median(
        values, weights, canonical_keys=keys
    ) == float(legacy_values[legacy_index])


def test_runtime_timing_recorder_writes_required_context(tmp_path: Path) -> None:
    recorder = RuntimeTimingRecorder(
        outer_split_id="split_001", policy_id="broad_data_qualified"
    )
    with recorder.measure("lightgbm_training", boosting_round=100) as row:
        row["output_rows"] = 123
    path = tmp_path / "runtime_timing.csv"
    recorder.write_csv(path)

    timing = pd.read_csv(path)
    assert timing.loc[0, "stage"] == "lightgbm_training"
    assert timing.loc[0, "outer_split_id"] == "split_001"
    assert timing.loc[0, "boosting_round"] == 100
    assert timing.loc[0, "output_rows"] == 123
    assert timing.loc[0, "wall_seconds"] >= 0
    assert timing.loc[0, "cpu_seconds"] >= 0


def test_lightgbm_max_round_checkpoint_predictions_match_independent_fits() -> None:
    lgb = pytest.importorskip("lightgbm")
    rng = np.random.default_rng(20260815)
    features = rng.normal(size=(600, 9))
    labels = rng.normal(size=600)
    validation = rng.normal(size=(180, 9))
    validation_labels = rng.normal(size=180)
    dates = np.repeat(pd.date_range("2024-01-02", periods=18), 10)
    metadata = pd.DataFrame(
        {
            "datetime": dates,
            "instrument": [f"asset_{index % 10:02d}" for index in range(180)],
            "__label": validation_labels,
        }
    )
    params = {
        "objective": "regression",
        "metric": "l2",
        "learning_rate": 0.05,
        "num_leaves": 15,
        "max_depth": 6,
        "min_data_in_leaf": 20,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 1,
        "deterministic": True,
        "force_col_wise": True,
        "seed": 20260725,
        "feature_fraction_seed": 20260725,
        "bagging_seed": 20260725,
        "data_random_seed": 20260725,
        "num_threads": 2,
        "verbosity": -1,
    }
    checkpoints = [5, 10, 20]
    shared_dataset = lgb.Dataset(features, label=labels, free_raw_data=False)
    max_booster = lgb.train(params, shared_dataset, num_boost_round=max(checkpoints))

    shared_metrics: list[dict[str, float]] = []
    independent_metrics: list[dict[str, float]] = []
    for checkpoint in checkpoints:
        shared_prediction = max_booster.predict(
            validation, num_iteration=checkpoint
        )
        independent = lgb.train(
            params,
            lgb.Dataset(features, label=labels),
            num_boost_round=checkpoint,
        )
        independent_prediction = independent.predict(validation)
        np.testing.assert_array_equal(shared_prediction, independent_prediction)
        shared_metrics.append(_validation_metrics(metadata, shared_prediction))
        independent_metrics.append(
            _validation_metrics(metadata, independent_prediction)
        )

    assert shared_metrics == independent_metrics
    assert int(
        np.argmax([row["mean_daily_rank_ic"] for row in shared_metrics])
    ) == int(
        np.argmax([row["mean_daily_rank_ic"] for row in independent_metrics])
    )
