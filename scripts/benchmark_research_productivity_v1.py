from __future__ import annotations

import argparse
import gc
import json
import shutil
import time
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from scipy.stats import spearmanr

from model_research.development_dry_run import _fit_from_spool
from model_research.fast_research import _profile_dates, load_fast_research_config
from model_research.feature_pool_experiment import _arm_factors, _array_hash
from model_research.feature_pool_policy import load_policy_config
from model_research.inputs import InputAccessAudit
from model_research.lightgbm_models import (
    _training_params,
    candidate_grid,
    load_lightgbm_config,
    select_lightgbm_candidate,
)
from model_research.linear_models import (
    _MemorySampler,
    _materialize_fold,
    _validation_metrics,
)
from model_research.lineage import resolve_authoritative_parents
from model_research.protocol import PROJECT_ROOT, parent_paths, resolve
from model_research.protocol_v1_1 import _labels_runtime_path, _matrix_authority
from model_research.research_cache import get_or_build_projection_spools
from model_research.runtime_timing import RuntimeTimingRecorder
from research_validation.feature_matrix import canonical_hash, file_sha256


def _resolve(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def _fresh_child(path: Path, root: Path) -> None:
    target = path.resolve()
    allowed = root.resolve()
    if target == allowed or allowed not in target.parents:
        raise ValueError("benchmark runtime path escapes controlled root")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=False)


def run_cache_benchmark(
    *, config_path: Path, cache_root: Path, runtime_root: Path, report_dir: Path
) -> None:
    import lightgbm as lgb

    if cache_root.exists():
        raise FileExistsError("cache benchmark requires a fresh cache root")
    profile = load_fast_research_config(config_path)
    policy_config = load_policy_config(resolve(profile["parents"]["policy_config"]))
    lightgbm_config = load_lightgbm_config(
        resolve(policy_config["parents"]["lightgbm_config"])
    )
    protocol_config = yaml.safe_load(
        resolve(lightgbm_config["protocol_config"]).read_text(encoding="utf-8")
    )
    resolution = resolve_authoritative_parents(parent_paths(protocol_config))
    split_id = "split_001"
    policy_id = "broad_data_qualified"
    feature_manifest = pd.read_csv(resolve(profile["parents"]["feature_manifest"]))
    factors = _arm_factors(feature_manifest, split_id=split_id, policy_id=policy_id)
    matrix = _matrix_authority(
        protocol_config, selected_factors=factors, verify_hashes=True
    )
    labels_path = _labels_runtime_path(protocol_config, resolution)
    dates = {
        fold: _profile_dates(
            profile=profile,
            protocol_config=protocol_config,
            split_id=split_id,
            fold=fold,
        )
        for fold in ("train", "validation")
    }
    rows: list[dict[str, Any]] = []
    parity: list[dict[str, Any]] = []
    for run_type in ("cold", "warm"):
        timing = RuntimeTimingRecorder(
            execution_class="benchmark",
            execution_profile="projection_spool_cache_v1",
            outer_split_id=split_id,
            policy_id=policy_id,
            feature_count=len(factors),
            execution_dtype="float64",
            thread_count=1,
        )
        audit = InputAccessAudit()
        runtime_dir = runtime_root / run_type
        _fresh_child(runtime_dir, runtime_root)
        started = time.perf_counter()
        with _MemorySampler() as sampler:
            cached = {
                fold: get_or_build_projection_spools(
                    cache_root=cache_root,
                    protocol_config=protocol_config,
                    resolution=resolution,
                    matrix=matrix,
                    split_id=split_id,
                    fold=fold,
                    dates=dates[fold],
                    factors=factors,
                    labels_path=labels_path,
                    audit=audit,
                    timing_recorder=timing,
                )
                for fold in ("train", "validation")
            }
            with timing.measure("preprocessing_fit", fold="train"):
                preprocessing = _fit_from_spool(
                    list(cached["train"].spool_paths), factors
                )
            materialized = {}
            for fold in ("train", "validation"):
                with timing.measure(f"{fold}_transform", fold=fold):
                    materialized[fold] = _materialize_fold(
                        spool_paths=list(cached[fold].spool_paths),
                        factors=factors,
                        preprocessing=preprocessing,
                        output_dir=runtime_dir,
                        name=fold,
                        keep_metadata=fold == "validation",
                    )
        wall_seconds = time.perf_counter() - started
        candidate = next(
            row
            for row in candidate_grid(lightgbm_config)
            if row["structural_row_id"] == "structure_01"
            and int(row["num_boost_round"]) == 100
        )
        dataset = lgb.Dataset(
            materialized["train"].features,
            label=materialized["train"].target,
            weight=materialized["train"].weights,
            feature_name=factors,
            free_raw_data=False,
            params={
                "feature_pre_filter": False,
                "data_random_seed": int(
                    lightgbm_config["determinism"]["data_random_seed"]
                ),
            },
        )
        dataset.construct()
        model = lgb.train(
            _training_params(lightgbm_config, candidate),
            dataset,
            num_boost_round=100,
        )
        prediction = model.predict(materialized["validation"].features)
        downstream_metrics = _validation_metrics(
            materialized["validation"].metadata, prediction
        )
        frame = timing.frame()
        rows.append(
            {
                "case": "split_001_broad_fast_scope",
                "run_type": run_type,
                "feature_count": len(factors),
                "train_date_count": len(dates["train"]),
                "validation_date_count": len(dates["validation"]),
                "cache_hit": all(value.cache_hit for value in cached.values()),
                "feature_projection_wall_seconds": float(
                    frame.loc[frame["stage"].eq("feature_projection"), "wall_seconds"].sum()
                ),
                "spool_wall_seconds": float(
                    frame.loc[frame["stage"].eq("feature_spooling"), "wall_seconds"].sum()
                ),
                "cache_validation_wall_seconds": float(
                    frame.loc[
                        frame["stage"].eq("projection_spool_cache_validation"),
                        "wall_seconds",
                    ].sum()
                ),
                "pre_model_preparation_wall_seconds": wall_seconds,
                "peak_rss_mib": sampler.peak_mb,
                "cache_disk_bytes": sum(value.disk_bytes for value in cached.values()),
                "test_read_count": audit.test_read_count,
            }
        )
        parity.append(
            {
                "run_type": run_type,
                "train_features_sha256": file_sha256(runtime_dir / "train_features.npy"),
                "train_target_sha256": file_sha256(runtime_dir / "train_target.npy"),
                "train_weights_sha256": file_sha256(runtime_dir / "train_weights.npy"),
                "validation_features_sha256": file_sha256(
                    runtime_dir / "validation_features.npy"
                ),
                "validation_target_sha256": file_sha256(
                    runtime_dir / "validation_target.npy"
                ),
                "validation_weights_sha256": file_sha256(
                    runtime_dir / "validation_weights.npy"
                ),
                "feature_order_sha256": canonical_hash(factors),
                "cache_keys_sha256": canonical_hash(
                    [cached[fold].cache_key for fold in ("train", "validation")]
                ),
                "downstream_prediction_sha256": _array_hash(prediction),
                "downstream_metrics_sha256": canonical_hash(downstream_metrics),
            }
        )
        del materialized, preprocessing, model, dataset, prediction
        gc.collect()
        shutil.rmtree(runtime_dir)
    benchmark = pd.DataFrame(rows)
    benchmark["cold_to_warm_speedup"] = (
        benchmark.loc[benchmark["run_type"].eq("cold"), "pre_model_preparation_wall_seconds"].iloc[0]
        / benchmark.loc[benchmark["run_type"].eq("warm"), "pre_model_preparation_wall_seconds"].iloc[0]
    )
    parity_frame = pd.DataFrame(parity)
    parity_columns = [column for column in parity_frame if column != "run_type"]
    parity_equal = all(parity_frame[column].nunique() == 1 for column in parity_columns)
    benchmark["materialized_numerical_parity"] = parity_equal
    report_dir.mkdir(parents=True, exist_ok=True)
    benchmark.to_csv(report_dir / "cache_benchmark.csv", index=False)
    (report_dir / "cache_parity.json").write_text(
        json.dumps(
            {
                "parity": parity_equal,
                "rows": parity,
                "test_scope_materialized": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _full_selected(development_root: Path, split_id: str, policy_id: str) -> pd.Series:
    metrics = pd.read_csv(development_root / split_id / policy_id / "validation_metrics.csv")
    return select_lightgbm_candidate(metrics)


def summarize_fast_runs(
    *, fast_root: Path, development_root: Path, report_dir: Path
) -> None:
    runs = sorted(path for path in fast_root.iterdir() if path.is_dir())
    calibration_rows = []
    benchmark_rows = []
    timing_frames = []
    for run in runs:
        receipt = json.loads((run / "fast_research_receipt.json").read_text(encoding="utf-8"))
        deltas = pd.read_csv(run / "paired_deltas.csv")
        summaries = pd.read_csv(run / "arm_summary.csv")
        timing_frames.append(pd.read_csv(run / "runtime_timing.csv"))
        baseline_id = receipt["baseline_id"]
        proposal_id = receipt["proposal_id"]
        full_wall = 0.0
        full_peak = 0.0
        for split_id in receipt["split_ids"]:
            baseline_full = _full_selected(development_root, split_id, baseline_id)
            proposal_full = _full_selected(development_root, split_id, proposal_id)
            fast_row = deltas.loc[deltas["outer_split_id"].eq(split_id)].iloc[0]
            full_delta = float(proposal_full["mean_daily_rank_ic"]) - float(
                baseline_full["mean_daily_rank_ic"]
            )
            fast_delta = float(fast_row["mean_daily_rank_ic_delta"])
            calibration_rows.append(
                {
                    "proposal_id": proposal_id,
                    "baseline_id": baseline_id,
                    "outer_split_id": split_id,
                    "fast_rank_ic_delta": fast_delta,
                    "full_development_rank_ic_delta": full_delta,
                    "rank_ic_delta_sign_agreement": (fast_delta > 0) == (full_delta > 0),
                    "fast_icir_delta": float(fast_row["daily_rank_ic_ir_delta"]),
                    "full_development_icir_delta": float(proposal_full["daily_rank_ic_ir"])
                    - float(baseline_full["daily_rank_ic_ir"]),
                }
            )
            for policy_id in (baseline_id, proposal_id):
                resource = pd.read_csv(
                    development_root / split_id / policy_id / "resource_summary.csv"
                ).iloc[0]
                full_wall += float(resource["wall_seconds"])
                full_peak = max(full_peak, float(resource["peak_rss_mib"]))
        fast_wall = float(summaries["wall_seconds"].sum())
        benchmark_rows.append(
            {
                "proposal_id": proposal_id,
                "baseline_id": baseline_id,
                "split_count": len(receipt["split_ids"]),
                "fast_pair_wall_seconds": fast_wall,
                "representative_full_pair_wall_seconds": full_wall,
                "speedup": full_wall / fast_wall,
                "fast_peak_rss_mib": float(summaries["peak_rss_mib"].max()),
                "full_peak_rss_mib": full_peak,
                "promotion_status": receipt["promotion_status"],
                "test_feature_read_count": receipt["test_feature_read_count"],
                "test_label_read_count": receipt["test_label_read_count"],
                "historical_replay_count": receipt["historical_replay_count"],
                "portfolio_test_release_count": receipt["portfolio_test_release_count"],
            }
        )
    calibration = pd.DataFrame(calibration_rows)
    if len(calibration) > 1:
        correlation = float(
            spearmanr(
                calibration["fast_rank_ic_delta"],
                calibration["full_development_rank_ic_delta"],
            ).statistic
        )
    else:
        correlation = float("nan")
    calibration["overall_delta_spearman"] = correlation
    calibration["overall_sign_agreement"] = float(
        calibration["rank_ic_delta_sign_agreement"].mean()
    )
    proposal_order_fast = (
        calibration.groupby("proposal_id")["fast_rank_ic_delta"].mean().sort_values(ascending=False).index.tolist()
    )
    proposal_order_full = (
        calibration.groupby("proposal_id")["full_development_rank_ic_delta"].mean().sort_values(ascending=False).index.tolist()
    )
    calibration["proposal_order_agreement"] = proposal_order_fast == proposal_order_full
    report_dir.mkdir(parents=True, exist_ok=True)
    calibration.to_csv(report_dir / "fast_full_calibration.csv", index=False)
    benchmark = pd.DataFrame(benchmark_rows)
    benchmark.to_csv(report_dir / "fast_research_benchmark.csv", index=False)
    runtime_rows = []
    for row in benchmark.itertuples(index=False):
        runtime_rows.extend(
            [
                {
                    "proposal_id": row.proposal_id,
                    "execution_class": "exploratory_fast",
                    "wall_seconds": row.fast_pair_wall_seconds,
                    "peak_rss_mib": row.fast_peak_rss_mib,
                },
                {
                    "proposal_id": row.proposal_id,
                    "execution_class": "full_development_reference",
                    "wall_seconds": row.representative_full_pair_wall_seconds,
                    "peak_rss_mib": row.full_peak_rss_mib,
                },
            ]
        )
    pd.DataFrame(runtime_rows).to_csv(report_dir / "runtime_comparison.csv", index=False)
    pd.concat(timing_frames, ignore_index=True).to_csv(
        report_dir / "runtime_timing.csv", index=False
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark Research Productivity V1")
    parser.add_argument("--config", default="configs/fast_research_v1.yaml")
    parser.add_argument("--report-dir", default="reports/research_productivity_v1")
    parser.add_argument(
        "--cache-root", default="tmp/research_productivity_v1/cache_benchmark"
    )
    parser.add_argument(
        "--runtime-root", default="outputs/research_productivity_v1/runtime/cache_benchmark"
    )
    parser.add_argument(
        "--fast-root", default="outputs/research_productivity_v1/fast_runs/calibration"
    )
    parser.add_argument(
        "--development-root", default="outputs/ml_feature_pool_mvp_v1/development"
    )
    parser.add_argument("--cache-benchmark", action="store_true")
    parser.add_argument("--summarize-fast", action="store_true")
    args = parser.parse_args()
    if args.cache_benchmark:
        run_cache_benchmark(
            config_path=_resolve(args.config),
            cache_root=_resolve(args.cache_root),
            runtime_root=_resolve(args.runtime_root),
            report_dir=_resolve(args.report_dir),
        )
    if args.summarize_fast:
        summarize_fast_runs(
            fast_root=_resolve(args.fast_root),
            development_root=_resolve(args.development_root),
            report_dir=_resolve(args.report_dir),
        )


if __name__ == "__main__":
    main()
