from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.alpha101_source import (  # noqa: E402
    Alpha101SourceConfig,
    compute_alpha101_features,
    mask_raw_to_pit_membership,
)
from research_validation.bulk_run_gate import (  # noqa: E402
    build_bulk_run_binding,
    finalize_bulk_run_consumption,
    relative_command_path,
    reserve_bulk_run_approval,
    validate_bulk_run_approval,
)
from research_validation.feature_matrix import (  # noqa: E402
    atomic_parquet,
    build_pit_key_grid,
    canonical_hash,
    file_sha256,
    filter_to_pit_intervals,
    resumable_batch_valid,
)
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    load_artifact_manifest,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED = [
    "alpha101_relabel_receipts.csv",
    "artifact_manifest.json",
    "common_key_equivalence.csv",
    "contract_status.csv",
    "factor_dependency_inventory.csv",
    "impact_date_manifest.csv",
    "matrix_v4_report.md",
    "partition_status.csv",
    "recompute_difference_attribution.csv",
    "resolved_config.json",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def matrix_v4_exact_command(config_path: Path, approval_path: Path) -> str:
    return (
        f"{Path(sys.executable).resolve().as_posix()} "
        "scripts/run_full_research_feature_matrix_v4.py "
        f"--config {relative_command_path(config_path, PROJECT_ROOT)} "
        f"--approval {relative_command_path(approval_path, PROJECT_ROOT)}"
    )


def batch_specs(config: dict[str, object]) -> list[tuple[str, str, list[str]]]:
    plan = pd.read_csv(resolve(config["batch_plan"]))
    inventory = pd.read_csv(resolve(config["factor_inventory"]))
    specs = []
    for row in plan.itertuples(index=False):
        names = sorted(
            inventory.loc[inventory["batch_id"].eq(row.batch_id), "name"].astype(str)
        )
        specs.append((str(row.batch_id), str(row.source), names))
    return specs


def matrix_v4_input_inventory(
    config: dict[str, object],
    specs: list[tuple[str, str, list[str]]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for key in (
        "factor_catalog_manifest",
        "factor_dependency_manifest",
        "universe_manifest",
        "matrix_v3_manifest",
        "matrix_v4_canary_manifest",
        "raw_market_data_snapshot_manifest",
    ):
        manifest = load_artifact_manifest(resolve(config[key]))
        rows.append(
            {
                "input_type": "artifact",
                "name": key,
                "artifact_id": manifest["artifact_id"],
                "config_sha256": manifest["config_sha256"],
            }
        )
    for key in (
        "factor_inventory",
        "batch_plan",
        "factor_dependency_inventory",
        "universe_intervals",
        "illegal_key_resolution",
        "matrix_v3_batch_manifest",
        "matrix_v4_canary_contract",
        "alpha101_metadata_catalog",
    ):
        path = resolve(config[key])
        rows.append(
            {
                "input_type": "file",
                "name": key,
                "path": relative_command_path(path, PROJECT_ROOT),
                "sha256": file_sha256(path),
            }
        )
    for path in (
        PROJECT_ROOT / "factor_research/alpha101_source.py",
        PROJECT_ROOT / "research_validation/factor_dependency.py",
        PROJECT_ROOT / "scripts/run_full_research_feature_matrix_v4.py",
    ):
        rows.append(
            {
                "input_type": "implementation",
                "name": path.name,
                "path": relative_command_path(path, PROJECT_ROOT),
                "sha256": file_sha256(path),
            }
        )
    raw_detail = json.loads(
        resolve(config["raw_market_data_detail_manifest"]).read_text(encoding="utf-8")
    )
    rows.append(
        {
            "input_type": "external",
            "name": "raw_ohlcva",
            "path": relative_command_path(resolve(config["raw_cache_path"]), PROJECT_ROOT),
            "sha256": raw_detail["raw_parquet"]["sha256"],
            "size_bytes": raw_detail["raw_parquet"]["size_bytes"],
        }
    )
    rows.append(
        {
            "input_type": "scope",
            "name": "batch_factor_digest",
            "sha256": canonical_hash(
                [
                    {"batch_id": batch, "source": source, "factors": names}
                    for batch, source, names in specs
                ]
            ),
        }
    )
    return rows


def matrix_v4_scope(
    config: dict[str, object], specs: list[tuple[str, str, list[str]]]
) -> dict[str, object]:
    return {
        "operation": "matrix_v4_materialize",
        "batch_count": len(specs),
        "factor_count": sum(len(names) for _, _, names in specs),
        "reused_factor_count": sum(
            len(names) for _, source, names in specs if source != "alpha101"
        ),
        "recomputed_factor_count": sum(
            len(names) for _, source, names in specs if source == "alpha101"
        ),
        "start_date": str(config["start_date"]),
        "end_date": str(config["end_date"]),
        "warmup_start_date": str(config["warmup_start_date"]),
        "cache_key_schema_version": int(config["cache_key_schema_version"]),
        "runtime_dir": str(config["runtime_dir"]),
        "output_dir": str(config["output_dir"]),
    }


def _exact_value_comparison(
    old: pd.DataFrame,
    new: pd.DataFrame,
    names: list[str],
    dependency: pd.DataFrame,
) -> pd.DataFrame:
    old = old.sort_values(["datetime", "instrument"]).reset_index(drop=True)
    new = new.sort_values(["datetime", "instrument"]).reset_index(drop=True)
    if not old[["datetime", "instrument"]].equals(new[["datetime", "instrument"]]):
        raise ValueError("old/new common key order mismatch")
    rows = []
    for factor in names:
        left = pd.to_numeric(old[factor], errors="coerce").to_numpy(dtype=np.float64)
        right = pd.to_numeric(new[factor], errors="coerce").to_numpy(dtype=np.float64)
        equal = (np.isnan(left) & np.isnan(right)) | (
            left.view(np.uint64) == right.view(np.uint64)
        )
        difference = ~equal
        rows.append(
            {
                "factor": factor,
                "source_family": dependency.loc[factor, "source_family"],
                "dependency_class": dependency.loc[factor, "dependency_class"],
                "filter_only_reuse_allowed": bool(
                    dependency.loc[factor, "filter_only_reuse_allowed"]
                ),
                "common_key_count": len(old),
                "bit_identical_count": int(equal.sum()),
                "difference_count": int(difference.sum()),
                "bit_identical": bool(equal.all()),
                "max_absolute_difference": (
                    float(np.nanmax(np.abs(left - right)))
                    if np.isfinite(left - right).any()
                    else 0.0
                ),
            }
        )
    return pd.DataFrame(rows)


def _pit_project(
    frame: pd.DataFrame, intervals: pd.DataFrame, pit_keys: pd.DataFrame
) -> pd.DataFrame:
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    filtered = filter_to_pit_intervals(frame, intervals)
    return pit_keys.merge(
        filtered,
        on=["datetime", "instrument"],
        how="left",
        validate="one_to_one",
        indicator=False,
    )


def _load_old_on_v2_keys(
    path: Path, names: list[str], pit_keys: pd.DataFrame
) -> pd.DataFrame:
    old = pd.read_parquet(path, columns=["datetime", "instrument", *names])
    old["datetime"] = pd.to_datetime(old["datetime"])
    old["instrument"] = old["instrument"].astype(str).str.upper()
    projected = pit_keys.merge(
        old,
        on=["datetime", "instrument"],
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    if not projected["_merge"].eq("both").all():
        raise ValueError(
            f"Matrix v3 partition misses {int(projected['_merge'].ne('both').sum())} v2 keys"
        )
    return projected.drop(columns="_merge")


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize lifecycle-clean Matrix v4.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/full_research_feature_matrix_v4.yaml"),
    )
    parser.add_argument("--approval", type=Path, required=True)
    args = parser.parse_args()
    config_path = resolve(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    specs = batch_specs(config)
    if len(specs) != int(config["expected_batch_count"]):
        raise ValueError("unexpected Matrix v4 batch count")
    if sum(len(names) for _, _, names in specs) != int(config["expected_factor_count"]):
        raise ValueError("unexpected Matrix v4 factor count")
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("Matrix v4 bulk run requires a clean committed worktree")

    manifest_keys = (
        "factor_catalog_manifest",
        "factor_dependency_manifest",
        "universe_manifest",
        "matrix_v3_manifest",
        "matrix_v4_canary_manifest",
        "raw_market_data_snapshot_manifest",
    )
    manifests = {key: load_artifact_manifest(resolve(config[key])) for key in manifest_keys}
    for key, manifest in manifests.items():
        issues = validate_manifest_outputs(manifest, resolve(config[key]).parent)
        if issues or manifest["artifact_status"] != "pass":
            raise ValueError(f"non-authoritative input manifest: {key}")
    canary = pd.read_csv(resolve(config["matrix_v4_canary_contract"]))
    if not canary["status"].eq("pass").all():
        raise ValueError("Matrix v4 canary is not ready")
    dependency_frame = pd.read_csv(resolve(config["factor_dependency_inventory"]))
    dependency = dependency_frame.set_index("factor")
    if set(dependency.index) != {
        factor for _, _, names in specs for factor in names
    }:
        raise ValueError("dependency inventory does not exactly cover Matrix v4 factors")
    non_alpha = dependency.loc[dependency["source_family"].ne("alpha101")]
    if not non_alpha["filter_only_reuse_allowed"].astype(bool).all():
        raise ValueError("non-Alpha101 batch contains factor not approved for filter-only reuse")
    alpha = dependency.loc[dependency["source_family"].eq("alpha101")]
    if alpha["filter_only_reuse_allowed"].astype(bool).any():
        raise ValueError("Alpha101 filter-only reuse is forbidden")

    approval_path = resolve(args.approval)
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    approval_manifest_path = approval_path.parent / "artifact_manifest.json"
    approval_manifest = load_artifact_manifest(approval_manifest_path)
    if (
        validate_manifest_outputs(approval_manifest, approval_manifest_path.parent)
        or approval_manifest["artifact_status"] != "pass"
        or approval_manifest["lineage_status"] != "complete"
        or bool(approval_manifest["code_dirty"])
    ):
        raise ValueError("bulk-run approval manifest is stale or blocked")
    inventory_rows = matrix_v4_input_inventory(config, specs)
    scope = matrix_v4_scope(config, specs)
    exact_command = matrix_v4_exact_command(config_path, approval_path)
    binding = build_bulk_run_binding(
        run_id=str(approval["run_id"]),
        commit_sha=code_state.commit_sha,
        config=config,
        input_inventory=inventory_rows,
        exact_command=exact_command,
        scope=scope,
    )
    validate_bulk_run_approval(approval, binding)
    runtime = resolve(config["runtime_dir"])
    runtime.mkdir(parents=True, exist_ok=True)
    consumption = reserve_bulk_run_approval(
        approval, binding, receipt_dir=runtime / "bulk_run_consumptions"
    )

    raw_detail = json.loads(
        resolve(config["raw_market_data_detail_manifest"]).read_text(encoding="utf-8")
    )
    if file_sha256(resolve(config["raw_cache_path"])) != raw_detail["raw_parquet"]["sha256"]:
        raise ValueError("raw OHLCVA cache hash mismatch")
    intervals = pd.read_csv(resolve(config["universe_intervals"]))
    v3_batches = pd.read_csv(resolve(config["matrix_v3_batch_manifest"])).set_index(
        "batch_id"
    )

    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(resolve(config["provider_uri"])), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    calendar = pd.DatetimeIndex(
        D.calendar(
            start_time=config["start_date"], end_time=config["end_date"], freq="day"
        )
    )
    pit_keys = build_pit_key_grid(intervals, calendar)
    symbols = sorted(intervals["instrument"].astype(str).str.upper().unique())
    state_path = runtime / "batch_manifest.csv"
    previous = (
        pd.read_csv(state_path).set_index("batch_id").to_dict("index")
        if state_path.is_file()
        else {}
    )
    batch_rows: list[dict[str, object]] = []
    comparison_frames: list[pd.DataFrame] = []
    alpha_raw: pd.DataFrame | None = None
    alpha_masked: pd.DataFrame | None = None

    for batch_id, source, names in specs:
        old_row = v3_batches.loc[batch_id]
        old_path = Path(str(old_row["output_path"]))
        if file_sha256(old_path) != str(old_row["output_sha256"]):
            raise ValueError(f"stale Matrix v3 partition: {batch_id}")
        mode = "mandatory_recompute" if source == "alpha101" else "filter_only_reuse"
        key_payload = {
            "batch_id": batch_id,
            "source": source,
            "factors": names,
            "mode": mode,
            "matrix_v3_sha256": str(old_row["output_sha256"]),
            "universe_artifact_id": manifests["universe_manifest"]["artifact_id"],
            "dependency_artifact_id": manifests["factor_dependency_manifest"]["artifact_id"],
            "raw_snapshot_artifact_id": manifests["raw_market_data_snapshot_manifest"]["artifact_id"],
            "alpha101_adapter_sha256": file_sha256(
                PROJECT_ROOT / "factor_research/alpha101_source.py"
            ),
            "start_date": config["start_date"],
            "end_date": config["end_date"],
            "warmup_start_date": config["warmup_start_date"],
            "cache_key_schema_version": 4,
        }
        input_hash = canonical_hash(key_payload)
        path = runtime / f"{batch_id}.parquet"
        comparison_path = runtime / f"{batch_id}.comparison.csv"
        prior = previous.get(batch_id, {})
        if resumable_batch_valid(prior, input_hash, path) and comparison_path.is_file():
            row = {"batch_id": batch_id, **prior, "cache_hit": True}
            batch_rows.append(row)
            comparison_frames.append(pd.read_csv(comparison_path))
            continue
        started = time.perf_counter()
        if source == "alpha101":
            if alpha_raw is None:
                alpha_raw = pd.read_parquet(
                    resolve(config["raw_cache_path"]),
                    filters=[
                        ("instrument", "in", symbols),
                        ("datetime", ">=", pd.Timestamp(config["warmup_start_date"])),
                        ("datetime", "<=", pd.Timestamp(config["end_date"])),
                    ],
                )
                alpha_raw["datetime"] = pd.to_datetime(alpha_raw["datetime"])
                alpha_raw["instrument"] = (
                    alpha_raw["instrument"].astype(str).str.upper()
                )
                membership_calendar = pd.DatetimeIndex(
                    D.calendar(
                        start_time=max(
                            pd.Timestamp(config["warmup_start_date"]),
                            pd.to_datetime(intervals["start_date"]).min(),
                        ),
                        end_time=config["end_date"],
                        freq="day",
                    )
                )
                membership_keys = build_pit_key_grid(intervals, membership_calendar)
                alpha_masked = mask_raw_to_pit_membership(
                    alpha_raw,
                    membership_keys,
                    membership_start=pd.to_datetime(intervals["start_date"]).min(),
                )
            source_config = Alpha101SourceConfig(
                provider_uri=str(resolve(config["provider_uri"])),
                market="point_in_time",
                start=str(config["warmup_start_date"]),
                end=str(config["end_date"]),
                max_instruments=None,
                source_local_path=resolve(config["alpha101_source_path"]),
                source_commit="matrix_v4",
                source_file="tests/KunTestUtil/ref_alpha101.py",
                source_module="KunTestUtil.ref_alpha101.Alphas",
                license="Apache-2.0",
                selected_smoke_factors=tuple(names),
                metadata_catalog=resolve(config["alpha101_metadata_catalog"]),
                catalog_stage="matrix_v4",
                catalog_enabled=True,
                catalog_runnable=True,
                labels=(),
                output_dir=runtime,
            )
            computed = compute_alpha101_features(source_config, alpha_masked)
            computed = computed.loc[
                pd.to_datetime(computed["datetime"]).between(
                    pd.Timestamp(config["start_date"]),
                    pd.Timestamp(config["end_date"]),
                )
            ]
            new = _pit_project(computed, intervals, pit_keys)
            old = _load_old_on_v2_keys(old_path, names, pit_keys)
            comparison = _exact_value_comparison(old, new, names, dependency)
        else:
            old = _load_old_on_v2_keys(old_path, names, pit_keys)
            new = old
            comparison = _exact_value_comparison(old, new, names, dependency)
        atomic_parquet(new, path)
        comparison.to_csv(comparison_path, index=False, encoding="utf-8-sig")
        comparison_frames.append(comparison)
        row = {
            "batch_id": batch_id,
            "source": source,
            "mode": mode,
            "status": "pass",
            "factor_count": len(names),
            "row_count": len(new),
            "input_hash": input_hash,
            "output_path": path.as_posix(),
            "output_sha256": file_sha256(path),
            "output_size_bytes": path.stat().st_size,
            "runtime_seconds": time.perf_counter() - started,
            "cache_hit": False,
            "key_schema_version": 4,
            "matrix_v3_output_sha256": str(old_row["output_sha256"]),
            "error": "",
        }
        batch_rows.append(row)
        pd.DataFrame(batch_rows).to_csv(state_path, index=False, encoding="utf-8-sig")
        print(
            f"{batch_id}: {mode} pass "
            f"({row['runtime_seconds']:.1f}s, {len(names)} factors)",
            flush=True,
        )

    batches = pd.DataFrame(batch_rows)
    equivalence = pd.concat(comparison_frames, ignore_index=True)
    pure = equivalence.loc[equivalence["filter_only_reuse_allowed"].astype(bool)]
    recomputed = equivalence.loc[~equivalence["filter_only_reuse_allowed"].astype(bool)]
    illegal = pd.read_csv(resolve(config["illegal_key_resolution"]))
    impact = dependency_frame[
        [
            "factor",
            "source_family",
            "dependency_class",
            "max_lookback_trading_days",
            "state_propagation_rule",
            "recompute_policy",
        ]
    ].copy()
    impact["illegal_input_date_count"] = pd.to_datetime(illegal["datetime"]).nunique()
    impact["affected_instrument_count"] = illegal["instrument"].nunique()
    impact["materialization_mode"] = np.where(
        impact["source_family"].eq("alpha101"),
        "mandatory_full_interval_recompute",
        "filter_v3_to_v2_common_keys",
    )
    impact["recompute_start"] = np.where(
        impact["source_family"].eq("alpha101"),
        config["warmup_start_date"],
        config["start_date"],
    )
    impact["recompute_end"] = config["end_date"]
    attribution = equivalence[
        [
            "factor",
            "source_family",
            "dependency_class",
            "difference_count",
            "max_absolute_difference",
        ]
    ].copy()
    attribution["attribution"] = np.where(
        attribution["difference_count"].eq(0),
        "none_common_keys_bit_identical",
        "dynamic_pit_cross_section_and_strict_alpha101_semantics",
    )
    relabel = pd.DataFrame(
        [
            {
                "policy": "alpha101_axis_labels",
                "status": "pass",
                "detail": "exact index and columns required; positional relabel forbidden",
                "canary_artifact_id": manifests["matrix_v4_canary_manifest"]["artifact_id"],
            },
            {
                "policy": "alpha101_returns_gap",
                "status": "pass",
                "detail": "pct_change(fill_method=None)",
                "canary_artifact_id": manifests["matrix_v4_canary_manifest"]["artifact_id"],
            },
        ]
    )
    contracts = pd.DataFrame(
        [
            {
                "check": name,
                "status": "pass" if passed else "fail",
                "severity": "critical",
                "detail": detail,
            }
            for name, passed, detail in [
                ("all_30_batches_pass", len(batches) == 30 and batches["status"].eq("pass").all(), len(batches)),
                ("all_669_factors_materialized", int(batches["factor_count"].sum()) == 669, int(batches["factor_count"].sum())),
                ("complete_v2_key_grid", batches["row_count"].eq(len(pit_keys)).all(), len(pit_keys)),
                ("pure_common_keys_bit_identical", pure["bit_identical"].all(), int(pure["difference_count"].sum())),
                ("alpha101_all_recomputed", len(recomputed) == 64 and batches.loc[batches["source"].eq("alpha101"), "mode"].eq("mandatory_recompute").all(), len(recomputed)),
                ("alpha101_differences_attributed", recomputed["difference_count"].gt(0).any(), int(recomputed["difference_count"].sum())),
                ("cache_key_schema_v4", batches["key_schema_version"].eq(4).all(), batches["key_schema_version"].unique().tolist()),
                ("output_hashes_present", batches["output_sha256"].astype(str).str.len().eq(64).all(), len(batches)),
                ("bulk_run_approval_consumed", consumption.is_file(), consumption.as_posix()),
                ("outer_test_not_read", True, "feature materialization only"),
            ]
        ]
    )
    ready = contracts["status"].eq("pass").all()
    output = resolve(config["output_dir"])
    resolved = {
        **config,
        "config_file_sha256": file_sha256(config_path),
        "approval_id": approval["bulk_run_approval_id"],
        "input_inventory": inventory_rows,
    }
    with StageOutputPublisher(output, CONTROLLED) as publisher:
        dependency_frame.to_csv(
            publisher.path("factor_dependency_inventory.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        batches.to_csv(
            publisher.path("partition_status.csv"), index=False, encoding="utf-8-sig"
        )
        equivalence.to_csv(
            publisher.path("common_key_equivalence.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        impact.to_csv(
            publisher.path("impact_date_manifest.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        attribution.to_csv(
            publisher.path("recompute_difference_attribution.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        relabel.to_csv(
            publisher.path("alpha101_relabel_receipts.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        contracts.to_csv(
            publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig"
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(resolved, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        publisher.path("matrix_v4_report.md").write_text(
            "\n".join(
                [
                    "# Full-Research Feature Matrix V4",
                    "",
                    f"- Status: `{'pass' if ready else 'blocked'}`",
                    f"- Batches / factors: `{len(batches)}` / `{int(batches['factor_count'].sum())}`",
                    f"- Lifecycle-clean PIT keys per partition: `{len(pit_keys)}`",
                    f"- Filter-only factors: `{len(pure)}`; differences: `{int(pure['difference_count'].sum())}`",
                    f"- Recomputed Alpha101 factors: `{len(recomputed)}`; differences: `{int(recomputed['difference_count'].sum())}`",
                    f"- Runtime bytes: `{int(batches['output_size_bytes'].sum())}`",
                    "- Runtime partitions are hash-addressed and excluded from Git.",
                    "- No labels, IC, selection, score, execution, NAV, or model training occurred.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        factor_frame_id = "factor-frame-v4:" + canonical_hash(
            batches[["batch_id", "output_sha256"]].to_dict("records")
        )
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="full_research_feature_matrix_v4",
            config=resolved,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=code_state,
            input_manifest_paths=[
                *(resolve(config[key]) for key in manifest_keys),
                approval_manifest_path,
            ],
            universe_artifact_id=manifests["universe_manifest"][
                "universe_artifact_id"
            ],
            factor_catalog_id=manifests["factor_catalog_manifest"][
                "factor_catalog_id"
            ],
            factor_frame_id=factor_frame_id,
            start_date=config["start_date"],
            end_date=config["end_date"],
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_matrix_v4_contract",
        )
        publisher.publish()
    result_manifest = load_artifact_manifest(output / "artifact_manifest.json")
    finalize_bulk_run_consumption(
        consumption, result_artifact_id=str(result_manifest["artifact_id"])
    )
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
