from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from model_research.feature_pool_experiment import (
    FullDevelopmentExecutionOptions,
    run_development_arm,
)
from model_research.full_execution import qualified_full_execution_profile
from model_research.protocol import PROJECT_ROOT
from research_validation.feature_matrix import canonical_hash, file_sha256


POLICIES = (
    "strict_current_baseline",
    "current_plus_existing_conditional_signal",
    "broad_data_qualified",
)
EXACT_FILES = (
    "model.txt",
    "preprocessing.json",
    "validation_metrics.csv",
    "candidate_manifest.csv",
    "sample_eligibility_receipt.csv",
    "selected_hyperparameters.json",
    "feature_importance.csv",
)


def _resolve(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def _directory_bytes(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _arm_identity(path: Path) -> dict[str, Any]:
    receipt = json.loads((path / "arm_receipt.json").read_text(encoding="utf-8"))
    return {
        "preparation_identity": receipt["preparation_identity"],
        "mutation_identity": receipt["mutation_identity"],
        "exact_file_sha256": {name: file_sha256(path / name) for name in EXACT_FILES},
    }


def _run_profile(
    *,
    profile_id: str,
    output_root: Path,
    runtime_root: Path,
    projection_cache_root: Path,
    preprocessing_cache_root: Path,
    policy_config_path: Path,
    feature_manifest_path: Path,
    lightgbm_config: dict[str, Any],
    factor_batch_size: int,
    median_workers: int,
) -> None:
    cached = profile_id != "baseline_cache_off"
    options = FullDevelopmentExecutionOptions(
        execution_profile=f"full_research_acceleration_v3_{profile_id}",
        projection_cache_root=projection_cache_root if cached else None,
        preprocessing_cache_root=preprocessing_cache_root if cached else None,
        preprocessing_factor_batch_size=(16 if not cached else factor_batch_size),
        preprocessing_median_workers=(1 if not cached else median_workers),
        reuse_selected_prediction=cached,
        detailed_materialization_timing=True,
        lightgbm_config=lightgbm_config,
    )
    for policy_id in POLICIES:
        run_development_arm(
            policy_config_path=policy_config_path,
            feature_manifest_path=feature_manifest_path,
            split_id="split_001",
            policy_id=policy_id,
            development_root=output_root / profile_id,
            runtime_root=runtime_root / profile_id,
            execution_options=options,
            freeze_metadata={
                "performance_engineering_only": True,
                "full_acceleration_qualification_profile": profile_id,
            },
        )


def _finalize(
    *, output_root: Path, projection_cache_root: Path, preprocessing_cache_root: Path
) -> dict[str, Any]:
    profiles = ("baseline_cache_off", "cache_cold", "cache_warm")
    parity_rows = []
    resource_frames = []
    timing_frames = []
    for policy_id in POLICIES:
        baseline_dir = output_root / profiles[0] / "split_001" / policy_id
        baseline = _arm_identity(baseline_dir)
        for profile_id in profiles:
            arm_dir = output_root / profile_id / "split_001" / policy_id
            observed = _arm_identity(arm_dir)
            exact = observed == baseline
            parity_rows.append(
                {
                    "policy_id": policy_id,
                    "profile_id": profile_id,
                    "exact_parity": exact,
                    "first_divergence": "none" if exact else next(
                        key for key in baseline if baseline[key] != observed[key]
                    ),
                }
            )
            resource = pd.read_csv(arm_dir / "resource_summary.csv")
            resource.insert(0, "profile_id", profile_id)
            resource_frames.append(resource)
            timing = pd.read_csv(arm_dir / "runtime_timing.csv")
            timing.insert(0, "profile_id", profile_id)
            timing_frames.append(timing)
    parity = pd.DataFrame(parity_rows)
    if not parity["exact_parity"].all():
        raise ValueError("Full acceleration qualification failed exact parity")
    resources = pd.concat(resource_frames, ignore_index=True)
    timing = pd.concat(timing_frames, ignore_index=True)
    stage = (
        timing.groupby(["profile_id", "policy_id", "stage"], dropna=False)
        .agg(
            wall_seconds=("wall_seconds", "sum"),
            cpu_seconds=("cpu_seconds", "sum"),
            read_bytes=("read_bytes", "sum"),
            write_bytes=("write_bytes", "sum"),
        )
        .reset_index()
    )
    for frame, name in (
        (parity, "parity.csv"),
        (resources, "resource_summary.csv"),
        (timing, "runtime_timing.csv"),
        (stage, "stage_breakdown.csv"),
    ):
        frame.to_csv(output_root / name, index=False)
    summary = {
        "schema_version": 1,
        "stage_id": "full_research_acceleration_v3_qualification",
        "status": "pass",
        "exact_parity": True,
        "policies": list(POLICIES),
        "profiles": list(profiles),
        "projection_spool_cache_eligible": True,
        "preprocessing_fit_cache_eligible": True,
        "selected_prediction_reuse_eligible": True,
        "vectorized_transform_eligible": True,
        "authoritative_execution": False,
        "scientific_model_selection_authorized": False,
        "strategy_v2_authorized": False,
        "cache_disk_bytes": {
            "projection_spool": _directory_bytes(projection_cache_root),
            "preprocessing_fit": _directory_bytes(preprocessing_cache_root),
        },
        "output_sha256": {
            name: file_sha256(output_root / name)
            for name in (
                "parity.csv",
                "resource_summary.csv",
                "runtime_timing.csv",
                "stage_breakdown.csv",
            )
        },
    }
    summary["summary_sha256"] = canonical_hash(summary)
    (output_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Qualify Full 8T data/preprocessing acceleration with exact parity"
    )
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--projection-cache-root", required=True)
    parser.add_argument("--preprocessing-cache-root", required=True)
    parser.add_argument(
        "--execution-profile",
        default="configs/research_lightgbm_full_exact_mt_v2.yaml",
    )
    parser.add_argument("--policy-config", default="configs/ml_feature_pool_mvp_v1.yaml")
    parser.add_argument(
        "--feature-manifest",
        default="outputs/ml_feature_pool_mvp_v1/current/feature_pool_manifest.csv",
    )
    parser.add_argument("--factor-batch-size", type=int, default=64)
    parser.add_argument("--median-workers", type=int, default=4)
    parser.add_argument(
        "--profiles",
        nargs="+",
        choices=("baseline_cache_off", "cache_cold", "cache_warm"),
        default=["baseline_cache_off", "cache_cold", "cache_warm"],
    )
    args = parser.parse_args()
    output_root = _resolve(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    lightgbm_config, _ = qualified_full_execution_profile(
        _resolve(args.execution_profile)
    )
    for profile_id in args.profiles:
        _run_profile(
            profile_id=profile_id,
            output_root=output_root,
            runtime_root=_resolve(args.runtime_root),
            projection_cache_root=_resolve(args.projection_cache_root),
            preprocessing_cache_root=_resolve(args.preprocessing_cache_root),
            policy_config_path=_resolve(args.policy_config),
            feature_manifest_path=_resolve(args.feature_manifest),
            lightgbm_config=lightgbm_config,
            factor_batch_size=args.factor_batch_size,
            median_workers=args.median_workers,
        )
    if all((output_root / profile).is_dir() for profile in (
        "baseline_cache_off", "cache_cold", "cache_warm"
    )):
        summary = _finalize(
            output_root=output_root,
            projection_cache_root=_resolve(args.projection_cache_root),
            preprocessing_cache_root=_resolve(args.preprocessing_cache_root),
        )
        print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
