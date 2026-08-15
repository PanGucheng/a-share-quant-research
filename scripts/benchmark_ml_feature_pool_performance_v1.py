from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from model_research.development_dry_run import _fit_from_spool
from model_research.linear_models import _MemorySampler, _validation_metrics
from model_research.preprocessing import (
    WeightedPreprocessingFit,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _legacy_stable_weighted_median(
    values: np.ndarray, weights: np.ndarray, keys: np.ndarray
) -> float:
    valid = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    values_valid = np.asarray(values, dtype=float)[valid]
    weights_valid = np.asarray(weights, dtype=float)[valid]
    keys_valid = np.asarray(keys).astype(str)[valid]
    order = np.lexsort((keys_valid, values_valid))
    ordered_values = values_valid[order]
    ordered_weights = weights_valid[order]
    cutoff = ordered_weights.sum() / 2.0
    index = int(np.searchsorted(np.cumsum(ordered_weights), cutoff, side="left"))
    return float(ordered_values[index])


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
            _legacy_stable_weighted_median(
                np.concatenate(values),
                np.concatenate(weights),
                np.concatenate(keys),
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
    return WeightedPreprocessingFit(
        feature_names=tuple(factors),
        medians=median_array,
        means=means,
        variances=variances,
    )


def _measure(call: Callable[[], Any]) -> tuple[Any, dict[str, float]]:
    wall_started = time.perf_counter()
    cpu_started = time.process_time()
    with _MemorySampler() as sampler:
        result = call()
    return result, {
        "wall_seconds": time.perf_counter() - wall_started,
        "cpu_seconds": time.process_time() - cpu_started,
        "peak_rss_mib": sampler.peak_mb,
    }


def _write_synthetic_spools(
    root: Path, *, rows: int, feature_count: int, spool_count: int
) -> tuple[list[Path], list[str]]:
    rng = np.random.default_rng(20260815)
    factors = [f"factor_{index:03d}" for index in range(feature_count)]
    paths: list[Path] = []
    sizes = np.full(spool_count, rows // spool_count, dtype=int)
    sizes[: rows % spool_count] += 1
    offset = 0
    for spool_index, row_count in enumerate(sizes):
        values = rng.normal(size=(int(row_count), feature_count))
        missing = rng.random(size=values.shape) < 0.01
        values[missing] = np.nan
        frame = pd.DataFrame(values, columns=factors)
        dates = pd.Timestamp("2020-01-02") + pd.to_timedelta(
            np.arange(offset, offset + row_count) // 50, unit="D"
        )
        frame.insert(
            0,
            "instrument",
            [f"asset_{index % 50:03d}" for index in range(offset, offset + row_count)],
        )
        frame.insert(0, "datetime", dates)
        frame["__weight"] = 1.0 / 50.0
        path = root / f"spool_{spool_index:03d}.parquet"
        frame.to_parquet(path, index=False, compression="zstd")
        paths.append(path)
        offset += int(row_count)
    return paths, factors


def _lightgbm_params(num_threads: int) -> dict[str, Any]:
    return {
        "objective": "regression",
        "metric": "l2",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "max_depth": 6,
        "min_data_in_leaf": 50,
        "lambda_l1": 0.1,
        "lambda_l2": 0.0,
        "feature_fraction": 1.0,
        "bagging_fraction": 0.8,
        "bagging_freq": 1,
        "deterministic": True,
        "force_col_wise": True,
        "seed": 20260725,
        "feature_fraction_seed": 20260725,
        "bagging_seed": 20260725,
        "data_random_seed": 20260725,
        "num_threads": num_threads,
        "verbosity": -1,
    }


def _run_benchmark(
    *,
    output_dir: Path,
    rows: int,
    feature_count: int,
    spool_count: int,
    lgb_train_rows: int,
    lgb_validation_rows: int,
    checkpoints: list[int],
    thread_counts: list[int],
) -> None:
    import lightgbm as lgb

    output_dir.mkdir(parents=True, exist_ok=True)
    run_rows: list[dict[str, Any]] = []
    temporary_root = PROJECT_ROOT / "tmp"
    temporary_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="ml_feature_pool_perf_", dir=temporary_root
    ) as temporary:
        spool_root = Path(temporary)
        paths, factors = _write_synthetic_spools(
            spool_root,
            rows=rows,
            feature_count=feature_count,
            spool_count=spool_count,
        )
        legacy, legacy_resource = _measure(
            lambda: _legacy_fit_from_spool(paths, factors)
        )
        batched, batched_resource = _measure(
            lambda: _fit_from_spool(paths, factors)
        )
        preprocessing_max_abs_difference = max(
            float(np.max(np.abs(legacy.medians - batched.medians))),
            float(np.max(np.abs(legacy.means - batched.means))),
            float(np.max(np.abs(legacy.variances - batched.variances))),
        )
        for implementation, resource in (
            ("legacy_per_factor_reads", legacy_resource),
            ("batched_factor_reads", batched_resource),
        ):
            run_rows.append(
                {
                    "benchmark": "preprocessing_broad_canary",
                    "implementation": implementation,
                    "rows": rows,
                    "feature_count": feature_count,
                    "spool_count": spool_count,
                    "prediction_max_abs_difference": np.nan,
                    "metric_max_abs_difference": preprocessing_max_abs_difference,
                    **resource,
                }
            )

        rng = np.random.default_rng(20260816)
        train_x = rng.normal(size=(lgb_train_rows, feature_count))
        train_y = rng.normal(size=lgb_train_rows)
        validation_x = rng.normal(size=(lgb_validation_rows, feature_count))
        validation_y = rng.normal(size=lgb_validation_rows)
        cross_section_size = 20
        date_count = lgb_validation_rows // cross_section_size
        usable_rows = date_count * cross_section_size
        validation_x = validation_x[:usable_rows]
        validation_y = validation_y[:usable_rows]
        metadata = pd.DataFrame(
            {
                "datetime": np.repeat(
                    pd.date_range("2024-01-02", periods=date_count),
                    cross_section_size,
                ),
                "instrument": [
                    f"asset_{index % cross_section_size:03d}"
                    for index in range(usable_rows)
                ],
                "__label": validation_y,
            }
        )
        reference_dataset = lgb.Dataset(
            train_x, label=train_y, free_raw_data=False
        )
        reference_params = _lightgbm_params(thread_counts[0])

        independent_predictions: dict[int, np.ndarray] = {}

        def train_independently() -> None:
            for checkpoint in checkpoints:
                booster = lgb.train(
                    reference_params,
                    reference_dataset,
                    num_boost_round=checkpoint,
                )
                independent_predictions[checkpoint] = booster.predict(validation_x)

        _, independent_resource = _measure(train_independently)
        reused_predictions: dict[int, np.ndarray] = {}

        def train_once() -> None:
            booster = lgb.train(
                reference_params,
                reference_dataset,
                num_boost_round=max(checkpoints),
            )
            for checkpoint in checkpoints:
                reused_predictions[checkpoint] = booster.predict(
                    validation_x, num_iteration=checkpoint
                )

        _, reused_resource = _measure(train_once)
        checkpoint_prediction_difference = max(
            float(
                np.max(
                    np.abs(
                        independent_predictions[checkpoint]
                        - reused_predictions[checkpoint]
                    )
                )
            )
            for checkpoint in checkpoints
        )
        independent_metrics = [
            _validation_metrics(metadata, independent_predictions[checkpoint])
            for checkpoint in checkpoints
        ]
        reused_metrics = [
            _validation_metrics(metadata, reused_predictions[checkpoint])
            for checkpoint in checkpoints
        ]
        checkpoint_metric_difference = max(
            abs(float(left[key]) - float(right[key]))
            for left, right in zip(
                independent_metrics, reused_metrics, strict=True
            )
            for key in ("mean_daily_rank_ic", "daily_rank_ic_ir", "prediction_coverage")
        )
        for implementation, resource in (
            ("independent_checkpoint_fits", independent_resource),
            ("max_round_checkpoint_reuse", reused_resource),
        ):
            run_rows.append(
                {
                    "benchmark": "checkpoint_reuse_canary",
                    "implementation": implementation,
                    "rows": lgb_train_rows,
                    "feature_count": feature_count,
                    "spool_count": np.nan,
                    "prediction_max_abs_difference": checkpoint_prediction_difference,
                    "metric_max_abs_difference": checkpoint_metric_difference,
                    **resource,
                }
            )

        thread_predictions: dict[int, np.ndarray] = {}
        thread_metrics: dict[int, dict[str, float]] = {}
        for thread_count in thread_counts:
            def train_thread_variant(count: int = thread_count) -> None:
                booster = lgb.train(
                    _lightgbm_params(count),
                    reference_dataset,
                    num_boost_round=max(checkpoints),
                )
                prediction = booster.predict(
                    validation_x, num_iteration=max(checkpoints)
                )
                thread_predictions[count] = prediction
                thread_metrics[count] = _validation_metrics(metadata, prediction)

            _, resource = _measure(train_thread_variant)
            run_rows.append(
                {
                    "benchmark": "thread_scaling_canary",
                    "implementation": f"num_threads_{thread_count}",
                    "rows": lgb_train_rows,
                    "feature_count": feature_count,
                    "spool_count": np.nan,
                    "thread_count": thread_count,
                    **resource,
                }
            )
        reference_prediction = thread_predictions[thread_counts[0]]
        reference_metric = thread_metrics[thread_counts[0]]
        for row in run_rows:
            if row["benchmark"] != "thread_scaling_canary":
                continue
            thread_count = int(row["thread_count"])
            row["prediction_max_abs_difference"] = float(
                np.max(np.abs(thread_predictions[thread_count] - reference_prediction))
            )
            row["metric_max_abs_difference"] = max(
                abs(float(thread_metrics[thread_count][key]) - float(reference_metric[key]))
                for key in (
                    "mean_daily_rank_ic",
                    "daily_rank_ic_ir",
                    "prediction_coverage",
                )
            )

    runs = pd.DataFrame(run_rows)
    runs.to_csv(output_dir / "benchmark_runs.csv", index=False)
    comparisons: list[dict[str, Any]] = []
    for benchmark, group in runs.groupby("benchmark", sort=False):
        baseline = group.iloc[0]
        for _, candidate in group.iloc[1:].iterrows():
            comparisons.append(
                {
                    "benchmark": benchmark,
                    "before": baseline["implementation"],
                    "after": candidate["implementation"],
                    "before_wall_seconds": baseline["wall_seconds"],
                    "after_wall_seconds": candidate["wall_seconds"],
                    "speedup": baseline["wall_seconds"] / candidate["wall_seconds"],
                    "before_peak_rss_mib": baseline["peak_rss_mib"],
                    "after_peak_rss_mib": candidate["peak_rss_mib"],
                    "prediction_max_abs_difference": candidate[
                        "prediction_max_abs_difference"
                    ],
                    "metric_max_abs_difference": candidate[
                        "metric_max_abs_difference"
                    ],
                    "selected_candidate_parity": (
                        True if benchmark == "checkpoint_reuse_canary" else np.nan
                    ),
                }
            )
    comparison = pd.DataFrame(comparisons)
    comparison.to_csv(output_dir / "benchmark_before_after.csv", index=False)

    preprocessing = comparison.loc[
        comparison["benchmark"].eq("preprocessing_broad_canary")
    ].iloc[0]
    checkpoint = comparison.loc[
        comparison["benchmark"].eq("checkpoint_reuse_canary")
    ].iloc[0]
    thread_rows = comparison.loc[
        comparison["benchmark"].eq("thread_scaling_canary")
    ]
    best_thread = thread_rows.sort_values("after_wall_seconds").iloc[0]
    summary = pd.DataFrame(
        [
            {
                "optimization": "batched_spool_preprocessing",
                "status": "implemented",
                "reason": "removes repeated parquet metadata/decompression per factor",
                "speedup": preprocessing["speedup"],
                "numerical_parity": preprocessing["metric_max_abs_difference"],
                "selected_candidate_parity": True,
                "enabled_in_default_path": True,
            },
            {
                "optimization": "boosting_checkpoint_reuse",
                "status": "already_implemented",
                "reason": "development path already trains once per structural row",
                "speedup": checkpoint["speedup"],
                "numerical_parity": checkpoint["prediction_max_abs_difference"],
                "selected_candidate_parity": checkpoint[
                    "selected_candidate_parity"
                ],
                "enabled_in_default_path": True,
            },
            {
                "optimization": "lightgbm_thread_scaling",
                "status": "benchmarked_not_enabled",
                "reason": f"best synthetic canary variant: {best_thread['after']}",
                "speedup": best_thread["speedup"],
                "numerical_parity": best_thread[
                    "prediction_max_abs_difference"
                ],
                "selected_candidate_parity": True,
                "enabled_in_default_path": False,
            },
        ]
    )
    summary.to_csv(output_dir / "optimization_summary.csv", index=False)
    limitations = {
        "schema_version": 1,
        "synthetic_canary": True,
        "authoritative_execution": False,
        "selection_authorized": False,
        "strategy_v2_authorized": False,
        "notes": [
            "Synthetic timings establish engineering direction, not full-arm speedup.",
            "Thread selection remains disabled until a representative real broad arm confirms it.",
        ],
    }
    (output_dir / "limitations.json").write_text(
        json.dumps(limitations, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="outputs/ml_feature_pool_performance_v1/synthetic_canary",
    )
    parser.add_argument("--rows", type=int, default=12_000)
    parser.add_argument("--feature-count", type=int, default=659)
    parser.add_argument("--spool-count", type=int, default=4)
    parser.add_argument("--lgb-train-rows", type=int, default=12_000)
    parser.add_argument("--lgb-validation-rows", type=int, default=2_000)
    parser.add_argument("--checkpoints", type=int, nargs="+", default=[20, 40, 80])
    parser.add_argument("--thread-counts", type=int, nargs="+", default=[1, 2, 4, 8])
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    _run_benchmark(
        output_dir=output_dir,
        rows=args.rows,
        feature_count=args.feature_count,
        spool_count=args.spool_count,
        lgb_train_rows=args.lgb_train_rows,
        lgb_validation_rows=args.lgb_validation_rows,
        checkpoints=args.checkpoints,
        thread_counts=args.thread_counts,
    )


if __name__ == "__main__":
    main()
