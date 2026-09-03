from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd
import yaml

from model_research.development_dry_run import _fit_from_spool
from model_research.feature_pool_experiment import _arm_factors
from model_research.full_execution import qualified_full_execution_profile
from model_research.inputs import InputAccessAudit, load_fold_dates
from model_research.lineage import resolve_authoritative_parents
from model_research.linear_models import _MemorySampler, _preprocessing_payload
from model_research.protocol import PROJECT_ROOT, parent_paths, resolve
from model_research.protocol_v1_1 import _labels_runtime_path, _matrix_authority
from model_research.research_cache import get_or_build_projection_spools
from research_validation.feature_matrix import canonical_hash, file_sha256


def _resolve(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark exact cold Full preprocessing batch/worker combinations"
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--cache-root", required=True)
    parser.add_argument(
        "--execution-profile",
        default="configs/research_lightgbm_full_exact_mt_v2.yaml",
    )
    parser.add_argument("--policy-config", default="configs/ml_feature_pool_mvp_v1.yaml")
    parser.add_argument(
        "--feature-manifest",
        default="outputs/ml_feature_pool_mvp_v1/current/feature_pool_manifest.csv",
    )
    parser.add_argument("--policy-id", default="broad_data_qualified")
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=[16, 32, 64, 128])
    parser.add_argument("--worker-counts", type=int, nargs="+", default=[1, 2, 4, 8])
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()
    output_dir = _resolve(args.output_dir)
    if output_dir.exists():
        raise FileExistsError("preprocessing benchmark outputs are immutable")
    output_dir.mkdir(parents=True)
    lightgbm_config, qualification = qualified_full_execution_profile(
        _resolve(args.execution_profile)
    )
    protocol = yaml.safe_load(resolve(lightgbm_config["protocol_config"]).read_text(encoding="utf-8"))
    resolution = resolve_authoritative_parents(parent_paths(protocol))
    factors = _arm_factors(
        pd.read_csv(_resolve(args.feature_manifest)),
        split_id="split_001",
        policy_id=args.policy_id,
    )
    matrix = _matrix_authority(protocol, selected_factors=factors, verify_hashes=True)
    dates = load_fold_dates(
        parent_paths(protocol).selection_date_assignments,
        outer_split_id="split_001",
        fold="train",
    )
    cached = get_or_build_projection_spools(
        cache_root=_resolve(args.cache_root),
        protocol_config=protocol,
        resolution=resolution,
        matrix=matrix,
        split_id="split_001",
        fold="train",
        dates=dates,
        factors=factors,
        labels_path=_labels_runtime_path(protocol, resolution),
        audit=InputAccessAudit(),
    )
    row_count = sum(
        len(pd.read_parquet(path, columns=["__weight"])) for path in cached.spool_paths
    )
    rows = []
    reference_hash = ""
    for batch_size in args.batch_sizes:
        for workers in args.worker_counts:
            for repeat in range(args.repeats):
                started = time.perf_counter()
                cpu_started = time.process_time()
                with _MemorySampler() as sampler:
                    fitted = _fit_from_spool(
                        list(cached.spool_paths),
                        factors,
                        factor_batch_size=batch_size,
                        median_workers=workers,
                    )
                payload_hash = canonical_hash(_preprocessing_payload(fitted))
                if not reference_hash:
                    reference_hash = payload_hash
                rows.append(
                    {
                        "policy_id": args.policy_id,
                        "factor_count": len(factors),
                        "row_count": row_count,
                        "factor_batch_size": batch_size,
                        "median_workers": workers,
                        "repeat": repeat,
                        "wall_seconds": time.perf_counter() - started,
                        "cpu_seconds": time.process_time() - cpu_started,
                        "peak_rss_mib": sampler.peak_mb,
                        "preprocessing_payload_sha256": payload_hash,
                        "exact_parity": payload_hash == reference_hash,
                    }
                )
    frame = pd.DataFrame(rows)
    frame.to_csv(output_dir / "benchmark_runs.csv", index=False)
    aggregate = (
        frame.groupby(["factor_batch_size", "median_workers"])
        .agg(
            mean_wall_seconds=("wall_seconds", "mean"),
            min_wall_seconds=("wall_seconds", "min"),
            mean_cpu_seconds=("cpu_seconds", "mean"),
            peak_rss_mib=("peak_rss_mib", "max"),
            exact_parity=("exact_parity", "all"),
        )
        .reset_index()
        .sort_values(["mean_wall_seconds", "peak_rss_mib"])
    )
    aggregate.to_csv(output_dir / "benchmark_summary.csv", index=False)
    winner = aggregate.loc[aggregate["exact_parity"]].iloc[0].to_dict()
    summary = {
        "schema_version": 1,
        "stage_id": "full_preprocessing_benchmark_v3",
        "status": "pass" if bool(frame["exact_parity"].all()) else "blocked",
        "policy_id": args.policy_id,
        "factor_count": len(factors),
        "projection_cache_key": cached.cache_key,
        "full_mt_qualification_sha256": qualification["summary_sha256"],
        "reference_preprocessing_sha256": reference_hash,
        "winner": winner,
        "output_sha256": {
            name: file_sha256(output_dir / name)
            for name in ("benchmark_runs.csv", "benchmark_summary.csv")
        },
    }
    summary["summary_sha256"] = canonical_hash(summary)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
