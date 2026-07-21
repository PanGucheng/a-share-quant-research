from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.alpha101_source import Alpha101SourceConfig, compute_alpha101_features  # noqa: E402
from factor_research.catalog import load_factor_catalog  # noqa: E402
from factor_research.factor_library import BASE_FIELDS, add_basic_factors  # noqa: E402
from factor_research.ta_source import import_ta_wrapper  # noqa: E402
from qlib_integration.contracts import contract_row  # noqa: E402
from research_validation.bulk_run_gate import (  # noqa: E402
    build_bulk_run_binding,
    relative_command_path,
    validate_bulk_run_approval,
)
from research_validation.feature_matrix import atomic_parquet, build_pit_key_grid, canonical_hash, file_sha256, filter_to_pit_intervals, resumable_batch_valid  # noqa: E402
from research_validation.lineage import capture_code_state, load_artifact_manifest, validate_manifest_outputs, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED = [
    "artifact_manifest.json",
    "batch_manifest.csv",
    "contract_status.csv",
    "factor_coverage.csv",
    "factor_matrix_report.md",
    "factor_matrix_sample.csv",
    "failure_inventory.csv",
    "schema.json",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def matrix_exact_command(config_path: Path, approval_path: Path, run_purpose: str) -> str:
    python = Path(sys.executable).resolve().as_posix()
    config_arg = relative_command_path(config_path, PROJECT_ROOT)
    approval_arg = relative_command_path(approval_path, PROJECT_ROOT)
    return (
        f"{python} scripts/run_full_research_feature_matrix_v1.py "
        f"--config {config_arg} --approval {approval_arg} --run-purpose {run_purpose}"
    )


def matrix_input_inventory(
    config: dict[str, object],
    manifests: list[dict[str, object]],
    raw_detail: dict[str, object],
    source_detail: dict[str, object],
) -> list[dict[str, object]]:
    rows = [
        {
            "input_type": "artifact",
            "name": str(manifest["stage_id"]),
            "artifact_id": str(manifest["artifact_id"]),
            "config_sha256": str(manifest["config_sha256"]),
        }
        for manifest in manifests
    ]
    for name in ("factor_inventory", "batch_plan", "alpha158_inventory", "alpha360_inventory", "alpha101_metadata_catalog"):
        path = resolve(config[name])
        rows.append({"input_type": "file", "name": name, "path": relative_command_path(path, PROJECT_ROOT), "sha256": file_sha256(path)})
    rows.extend(
        [
            {"input_type": "external", "name": "raw_parquet", "sha256": str(raw_detail["raw_parquet"]["sha256"])},
            {"input_type": "external", "name": "provider_tree", "sha256": str(raw_detail["provider_tree_sha256"])},
            {"input_type": "external", "name": "qlib_commit", "value": str(source_detail["qlib_commit"])},
        ]
    )
    for source, material in sorted(source_detail["batch_key_material"].items()):
        rows.append({"input_type": "source_key", "name": source, **material})
    return rows


def matrix_run_scope(config: dict[str, object], batch_specs: list[tuple[str, str, list[str]]], run_purpose: str) -> dict[str, object]:
    return {
        "operation": run_purpose,
        "batch_count": len(batch_specs),
        "factor_count": sum(len(names) for _, _, names in batch_specs),
        "sources": sorted({source for _, source, _ in batch_specs}),
        "start_date": str(config["start_date"]),
        "end_date": str(config["end_date"]),
        "warmup_start_date": str(config["warmup_start_date"]),
        "cache_key_schema_version": int(config["cache_key_schema_version"]),
        "runtime_dir": str(config["runtime_dir"]),
        "output_dir": str(config["output_dir"]),
    }


def load_raw(config: dict[str, object], symbols: list[str], runtime: Path, D: object) -> pd.DataFrame:
    if config.get("raw_cache_path"):
        external = resolve(config["raw_cache_path"])
        if external.is_file():
            return pd.read_parquet(external)
    path = runtime / "raw_ohlcva.parquet"
    sidecar = runtime / "raw_ohlcva.json"
    input_hash = canonical_hash({"provider": str(config["provider_uri"]), "symbols": symbols, "start": config["warmup_start_date"], "end": config["end_date"], "fields": BASE_FIELDS})
    if path.is_file() and sidecar.is_file():
        state = json.loads(sidecar.read_text(encoding="utf-8"))
        if state.get("input_hash") == input_hash and state.get("output_sha256") == file_sha256(path):
            return pd.read_parquet(path)
    frame = D.features(symbols, BASE_FIELDS, start_time=config["warmup_start_date"], end_time=config["end_date"], freq="day").reset_index()
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    atomic_parquet(frame, path)
    sidecar.write_text(json.dumps({"input_hash": input_hash, "output_sha256": file_sha256(path)}, indent=2) + "\n", encoding="utf-8")
    return frame


def load_required_provenance(config: dict[str, object]) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    if int(config.get("cache_key_schema_version", 0)) != 3:
        raise ValueError("authoritative full-research matrix requires cache_key_schema_version=3")
    raw_manifest_path = resolve(config["raw_market_data_snapshot_manifest"])
    source_manifest_path = resolve(config["factor_source_provenance_manifest"])
    raw_manifest = load_artifact_manifest(raw_manifest_path)
    source_manifest = load_artifact_manifest(source_manifest_path)
    issues = [
        *validate_manifest_outputs(raw_manifest, raw_manifest_path.parent),
        *validate_manifest_outputs(source_manifest, source_manifest_path.parent),
    ]
    for name, manifest in (("raw", raw_manifest), ("source", source_manifest)):
        if manifest["artifact_status"] != "pass" or manifest["lineage_status"] != "complete" or bool(manifest["code_dirty"]):
            raise ValueError(f"{name} provenance is not authoritative: {manifest['artifact_id']}")
    if issues:
        raise ValueError("provenance output freshness failed: " + "; ".join(item.reason for item in issues))
    raw_detail = json.loads(resolve(config["raw_market_data_detail_manifest"]).read_text(encoding="utf-8"))
    source_detail = json.loads(resolve(config["factor_source_detail_manifest"]).read_text(encoding="utf-8"))
    source_inventory = pd.read_csv(source_manifest_path.parent / "source_file_inventory.csv")
    project_rows = source_inventory.loc[~source_inventory["file_role"].astype(str).str.startswith("repository:")]
    source_mismatches = []
    for row in project_rows.itertuples(index=False):
        path = PROJECT_ROOT / str(row.relative_path)
        if not path.is_file() or file_sha256(path) != str(row.sha256):
            source_mismatches.append(str(row.relative_path))
    if source_mismatches:
        raise ValueError(f"current project source differs from source provenance: {sorted(set(source_mismatches))}")
    raw_path = resolve(config["raw_cache_path"])
    if file_sha256(raw_path) != str(raw_detail["raw_parquet"]["sha256"]):
        raise ValueError("raw cache hash differs from raw market data snapshot")
    if str(source_detail["qlib_commit"]) != str(raw_detail["qlib_commit"]):
        raise ValueError("raw and source provenance use different Qlib commits")
    return raw_manifest, source_manifest, raw_detail, source_detail


def expression_batch(symbols: list[str], names: list[str], inventory_path: Path, start: object, end: object, D: object) -> pd.DataFrame:
    inventory = pd.read_csv(inventory_path).set_index("catalog_name")
    missing = sorted(set(names) - set(inventory.index))
    if missing:
        raise ValueError(f"expression inventory missing factors: {missing}")
    expressions = [str(inventory.loc[name, "expression"]) for name in names]
    frame = D.features(symbols, expressions, start_time=start, end_time=end, freq="day").reset_index()
    frame = frame.rename(columns=dict(zip(expressions, names)))
    return frame[["datetime", "instrument", *names]]


def ta_batch(raw: pd.DataFrame, names: list[str], source_path: Path) -> pd.DataFrame:
    import_ta_wrapper(source_path)
    from ta.wrapper import add_momentum_ta, add_trend_ta, add_volatility_ta, add_volume_ta

    functions = []
    if any(name.startswith("ta_volume_") for name in names): functions.append(add_volume_ta)
    if any(name.startswith("ta_volatility_") for name in names): functions.append(add_volatility_ta)
    if any(name.startswith("ta_trend_") for name in names): functions.append(add_trend_ta)
    if any(name.startswith("ta_momentum_") for name in names): functions.append(add_momentum_ta)
    renamed = raw.rename(columns={"$open": "open", "$high": "high", "$low": "low", "$close": "close", "$volume": "volume"})
    rows = []
    for instrument, group in renamed.groupby("instrument", sort=True):
        source = group[["datetime", "instrument", "open", "high", "low", "close", "volume"]].sort_values("datetime").copy()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            computed = source
            for function in functions:
                kwargs = {"fillna": False, "colprefix": "ta_", "vectorized": False}
                if function is add_volume_ta:
                    computed = function(computed, high="high", low="low", close="close", volume="volume", **kwargs)
                elif function is add_volatility_ta:
                    computed = function(computed, high="high", low="low", close="close", **kwargs)
                elif function is add_trend_ta:
                    computed = function(computed, high="high", low="low", close="close", **kwargs)
                else:
                    computed = function(computed, high="high", low="low", close="close", volume="volume", **kwargs)
        missing = sorted(set(names) - set(computed.columns))
        if missing:
            raise ValueError(f"TA wrapper missing selected factors: {missing}")
        rows.append(computed[["datetime", "instrument", *names]])
    return pd.concat(rows, ignore_index=True)


def alpha101_batch(raw: pd.DataFrame, names: list[str], config: dict[str, object], output: Path, source_commit: str) -> pd.DataFrame:
    source_config = Alpha101SourceConfig(
        provider_uri=str(resolve(config["provider_uri"])), market="point_in_time", start=str(config["warmup_start_date"]), end=str(config["end_date"]), max_instruments=None,
        source_local_path=resolve(config["alpha101_source_path"]), source_commit=source_commit, source_file="tests/KunTestUtil/ref_alpha101.py", source_module="KunTestUtil.ref_alpha101.Alphas", license="Apache-2.0",
        selected_smoke_factors=tuple(names), metadata_catalog=resolve(config["alpha101_metadata_catalog"]), catalog_stage="full_research_trial", catalog_enabled=True, catalog_runnable=True,
        labels=("label_10d_t1", "label_20d_t1"), output_dir=output,
    )
    return compute_alpha101_features(source_config, raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a resumable partitioned full-research factor matrix.")
    parser.add_argument("--config", type=Path, default=Path("configs/full_research_feature_matrix_v1.yaml"))
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--run-purpose", choices=("materialize", "cache_verify"), default="materialize")
    args = parser.parse_args()
    config_path = resolve(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    catalog_manifest = load_artifact_manifest(resolve(config["factor_catalog_manifest"]))
    universe_manifest = load_artifact_manifest(resolve(config["universe_manifest"]))
    raw_manifest, source_manifest, raw_detail, source_detail = load_required_provenance(config)
    entries = load_factor_catalog(resolve(config["factor_catalog"]))
    by_source: dict[str, list[str]] = {}
    for entry in entries:
        if entry.source_project == "qlib_alpha158": source = "alpha158"
        elif entry.source_project == "qlib_alpha360": source = "alpha360"
        elif entry.source_project == "ta": source = "ta"
        elif entry.source_project == "kunquant_alpha101": source = "alpha101"
        elif entry.source_project == "qlib_baseline_basic": source = "project_basic"
        else: raise ValueError(f"unsupported trial factor source: {entry.source_project}")
        by_source.setdefault(source, []).append(entry.name)
    if config.get("batch_plan") and config.get("factor_inventory"):
        plan = pd.read_csv(resolve(config["batch_plan"]))
        inventory = pd.read_csv(resolve(config["factor_inventory"]))
        batch_specs = []
        for row in plan.itertuples(index=False):
            names = sorted(inventory.loc[inventory["batch_id"].eq(row.batch_id), "name"].astype(str))
            batch_specs.append((str(row.batch_id), str(row.source), names))
    else:
        batch_specs = [(source, source, sorted(by_source.get(source, []))) for source in ["alpha158", "alpha360", "project_basic", "ta", "alpha101"]]
    selected_batch_ids = {str(item) for item in config.get("selected_batch_ids", [])}
    if selected_batch_ids:
        batch_specs = [item for item in batch_specs if item[0] in selected_batch_ids]
        if {item[0] for item in batch_specs} != selected_batch_ids:
            raise ValueError(f"unknown selected_batch_ids: {sorted(selected_batch_ids - {item[0] for item in batch_specs})}")
    if config.get("maximum_factors_per_selected_batch") is not None:
        limit = int(config["maximum_factors_per_selected_batch"])
        batch_specs = [(batch_id, source, names[:limit]) for batch_id, source, names in batch_specs]
    scoped_factor_count = sum(len(names) for _, _, names in batch_specs)
    bulk_run = len(batch_specs) > 5 or scoped_factor_count >= 100
    approval: dict[str, object] | None = None
    approval_manifest_path: Path | None = None
    if bulk_run:
        if args.approval is None:
            raise ValueError("large matrix run requires --approval bound to the exact command and inputs")
        approval_path = resolve(args.approval)
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
        approval_manifest_path = approval_path.parent / "artifact_manifest.json"
        approval_manifest = load_artifact_manifest(approval_manifest_path)
        approval_issues = validate_manifest_outputs(approval_manifest, approval_manifest_path.parent)
        if approval_issues or approval_manifest["artifact_status"] != "pass":
            raise ValueError("bulk run review bundle is stale or blocked")
        code_state_at_gate = capture_code_state(PROJECT_ROOT)
        if code_state_at_gate.dirty:
            raise ValueError("large matrix run requires a clean project worktree")
        input_inventory = matrix_input_inventory(
            config,
            [catalog_manifest, universe_manifest, raw_manifest, source_manifest],
            raw_detail,
            source_detail,
        )
        scope = matrix_run_scope(config, batch_specs, args.run_purpose)
        exact_command = matrix_exact_command(config_path, approval_path, args.run_purpose)
        binding = build_bulk_run_binding(
            run_id=str(approval["run_id"]),
            commit_sha=str(source_manifest["code_commit_sha"]),
            config=config,
            input_inventory=input_inventory,
            exact_command=exact_command,
            scope=scope,
        )
        validate_bulk_run_approval(approval, binding)
    intervals = pd.read_csv(resolve(config["universe_intervals"]))
    symbols = sorted(intervals["instrument"].astype(str).str.upper().unique())
    runtime = resolve(config["runtime_dir"])
    runtime.mkdir(parents=True, exist_ok=True)
    state_path = runtime / "batch_manifest.csv"
    previous = pd.read_csv(state_path).set_index("batch_id").to_dict("index") if state_path.is_file() else {}

    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D
    qlib.init(provider_uri=str(resolve(config["provider_uri"])), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    calendar = pd.DatetimeIndex(D.calendar(start_time=config["start_date"], end_time=config["end_date"], freq="day"))
    pit_keys = build_pit_key_grid(intervals, calendar)
    raw: pd.DataFrame | None = None
    batch_rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    for batch_id, source, names in batch_specs:
        path = runtime / f"{batch_id}.parquet"
        source_key = source_detail["batch_key_material"][source]
        key_payload = {
            "batch": batch_id,
            "source": source,
            "factors": names,
            "factor_catalog_artifact_id": catalog_manifest["artifact_id"],
            "universe_artifact_id": universe_manifest["artifact_id"],
            "market_data_snapshot_artifact_id": raw_manifest["artifact_id"],
            "source_provenance_artifact_id": source_manifest["artifact_id"],
            "source_specific_tree_hash": source_key["source_specific_tree_hash"],
            "adapter_hash": source_key["adapter_hash"],
            "formula_or_metadata_hash": source_key["formula_or_metadata_hash"],
            "qlib_commit": source_key["qlib_commit"],
            "warmup_start": config["warmup_start_date"],
            "start": config["start_date"],
            "end": config["end_date"],
            "key_schema_version": 3,
        }
        input_hash = canonical_hash(key_payload)
        prior = previous.get(batch_id, {})
        attempts = int(prior.get("attempts", 0))
        if resumable_batch_valid(prior, input_hash, path):
            batch_rows.append({"batch_id": batch_id, **prior, "cache_hit": True})
            continue
        started = time.perf_counter()
        attempts += 1
        try:
            reindexed_from_cache = False
            if source == "alpha158": frame = expression_batch(symbols, names, resolve(config["alpha158_inventory"]), config["start_date"], config["end_date"], D)
            elif source == "alpha360": frame = expression_batch(symbols, names, resolve(config["alpha360_inventory"]), config["start_date"], config["end_date"], D)
            else:
                if raw is None: raw = load_raw(config, symbols, runtime, D)
                if source == "project_basic": frame = add_basic_factors(raw.copy())[["datetime", "instrument", *names]]
                elif source == "ta": frame = ta_batch(raw, names, resolve(config["ta_source_path"]))
                else: frame = alpha101_batch(raw, names, config, runtime, str(source_key["source_commit"]))
            frame = frame.loc[pd.to_datetime(frame["datetime"]).between(pd.Timestamp(config["start_date"]), pd.Timestamp(config["end_date"]))]
            frame = filter_to_pit_intervals(frame, intervals)
            frame = pit_keys.merge(frame, on=["datetime", "instrument"], how="left", validate="one_to_one")
            atomic_parquet(frame, path)
            row = {"batch_id": batch_id, "source": source, "status": "pass", "factor_count": len(names), "row_count": len(frame), "instrument_count": frame["instrument"].nunique(), "start_date": frame["datetime"].min(), "end_date": frame["datetime"].max(), "input_hash": input_hash, "output_path": path.as_posix(), "output_sha256": file_sha256(path), "output_size_bytes": path.stat().st_size, "attempts": attempts, "runtime_seconds": time.perf_counter() - started, "cache_hit": False, "reindexed_from_cache": reindexed_from_cache, "key_schema_version": 3, "market_data_snapshot_artifact_id": raw_manifest["artifact_id"], "source_provenance_artifact_id": source_manifest["artifact_id"], "source_specific_tree_hash": source_key["source_specific_tree_hash"], "adapter_hash": source_key["adapter_hash"], "formula_or_metadata_hash": source_key["formula_or_metadata_hash"], "error": ""}
        except Exception as exc:
            row = {"batch_id": batch_id, "source": source, "status": "failed", "factor_count": len(names), "row_count": 0, "instrument_count": 0, "start_date": "", "end_date": "", "input_hash": input_hash, "output_path": path.as_posix(), "output_sha256": "", "output_size_bytes": 0, "attempts": attempts, "runtime_seconds": time.perf_counter() - started, "cache_hit": False, "reindexed_from_cache": False, "key_schema_version": 3, "market_data_snapshot_artifact_id": raw_manifest["artifact_id"], "source_provenance_artifact_id": source_manifest["artifact_id"], "source_specific_tree_hash": source_key["source_specific_tree_hash"], "adapter_hash": source_key["adapter_hash"], "formula_or_metadata_hash": source_key["formula_or_metadata_hash"], "error": f"{type(exc).__name__}: {exc}"}
            failures.append(row.copy())
        batch_rows.append(row)
        pd.DataFrame(batch_rows).to_csv(state_path, index=False, encoding="utf-8-sig")
    batch = pd.DataFrame(batch_rows)
    success = batch.loc[batch["status"].eq("pass")]
    coverage_rows = []
    sample: pd.DataFrame | None = None
    for row in success.itertuples(index=False):
        frame = pd.read_parquet(row.output_path)
        factor_columns = [column for column in frame.columns if column not in {"datetime", "instrument"}]
        for factor in factor_columns:
            coverage_rows.append({"batch_id": row.batch_id, "factor": factor, "valid_rows": int(frame[factor].notna().sum()), "total_rows": len(frame), "coverage": float(frame[factor].notna().mean())})
        subset = frame.head(20)
        sample = subset if sample is None else sample.merge(subset, on=["datetime", "instrument"], how="outer")
    coverage = pd.DataFrame(coverage_rows)
    factor_count = int(success["factor_count"].sum()) if not success.empty else 0
    contracts = pd.DataFrame([
        contract_row("factor_catalog_count", len(entries) == int(config.get("expected_factor_count", 80)), len(entries), int(config.get("expected_factor_count", 80))),
        contract_row("all_batches_pass", failures == [], len(failures), 0),
        contract_row("all_factors_materialized", factor_count == scoped_factor_count, factor_count, scoped_factor_count),
        contract_row("pit_universe_applied", bool(not success.empty and success["row_count"].gt(0).all()), universe_manifest["universe_artifact_id"], "nonempty PIT-filtered batches"),
        contract_row("complete_key_grid_aligned", bool(not success.empty and success["row_count"].eq(len(pit_keys)).all()), success["row_count"].tolist(), len(pit_keys)),
        contract_row("batch_output_hashes_present", bool(not success.empty and success["output_sha256"].astype(str).str.len().eq(64).all()), int(success["output_sha256"].astype(str).str.len().eq(64).sum()), len(success)),
        contract_row("resume_metadata_present", set(["input_hash", "attempts", "cache_hit", "key_schema_version"]).issubset(batch.columns), list(batch.columns), "input_hash/attempts/cache_hit/key_schema_version"),
        contract_row("cache_key_schema_v3", bool(not success.empty and success["key_schema_version"].eq(3).all()), success["key_schema_version"].tolist(), 3),
        contract_row("legacy_cache_not_reindexed", bool(not success.empty and ~success["reindexed_from_cache"].astype(bool).any()), int(success["reindexed_from_cache"].astype(bool).sum()), 0),
        contract_row("raw_provenance_bound", bool(not success.empty and success["market_data_snapshot_artifact_id"].eq(raw_manifest["artifact_id"]).all()), success["market_data_snapshot_artifact_id"].nunique(), 1),
        contract_row("source_provenance_bound", bool(not success.empty and success["source_provenance_artifact_id"].eq(source_manifest["artifact_id"]).all()), success["source_provenance_artifact_id"].nunique(), 1),
        contract_row("bulk_run_approval_valid", not bulk_run or approval is not None, approval.get("bulk_run_approval_id") if approval else "not_required", "valid approval or bounded canary"),
        contract_row("cache_verify_all_batches_hit", args.run_purpose != "cache_verify" or bool(not success.empty and success["cache_hit"].astype(bool).all()), int(success["cache_hit"].astype(bool).sum()), len(success) if args.run_purpose == "cache_verify" else "not_required"),
    ])
    ready = contracts["status"].eq("pass").all()
    output_dir = resolve(config["output_dir"])
    code_state = capture_code_state(PROJECT_ROOT)
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        batch.to_csv(publisher.path("batch_manifest.csv"), index=False, encoding="utf-8-sig")
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        coverage.to_csv(publisher.path("factor_coverage.csv"), index=False, encoding="utf-8-sig")
        (sample if sample is not None else pd.DataFrame()).to_csv(publisher.path("factor_matrix_sample.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(failures, columns=batch.columns).to_csv(publisher.path("failure_inventory.csv"), index=False, encoding="utf-8-sig")
        materialized_factors = sorted({name for _, _, names in batch_specs for name in names})
        publisher.path("schema.json").write_text(json.dumps({"keys": ["datetime", "instrument"], "factors": materialized_factors, "partitioning": "bounded source batches" if config.get("batch_plan") else "source adapter", "runtime_committed": False, "cache_key_schema_version": 3}, indent=2) + "\n", encoding="utf-8")
        publisher.path("factor_matrix_report.md").write_text(f"# Full-Research Feature Matrix V1\n\n- Status: `{'pass' if ready else 'blocked'}`\n- Factors: `{factor_count}` / `{scoped_factor_count}` in scope (`{len(entries)}` catalog total)\n- PIT instruments in source intervals: `{len(symbols)}`\n- Passed batches: `{len(success)}` / `{len(batch)}`\n- Run purpose: `{args.run_purpose}`\n- Bulk-run approval: `{approval.get('bulk_run_approval_id') if approval else 'not_required_bounded_canary'}`\n- Runtime partitions are hash-addressed and intentionally excluded from Git.\n", encoding="utf-8")
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        factor_frame_id = "factor-frame:" + canonical_hash(success[["batch_id", "output_sha256"]].to_dict("records"))
        input_manifest_paths = [resolve(config["factor_catalog_manifest"]), resolve(config["universe_manifest"]), resolve(config["raw_market_data_snapshot_manifest"]), resolve(config["factor_source_provenance_manifest"])]
        if approval_manifest_path is not None:
            input_manifest_paths.append(approval_manifest_path)
        write_stage_artifact_manifest(project_root=PROJECT_ROOT, stage_id="full_research_feature_matrix_v1", config=config, output_dir=publisher.staging_dir, output_files=files, code_state=code_state, input_manifest_paths=input_manifest_paths, factor_frame_id=factor_frame_id, start_date=config["start_date"], end_date=config["end_date"], lineage_status="complete", artifact_status="pass" if ready else "blocked", blocked_reason="" if ready else "blocked_feature_matrix_batch_failure")
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
