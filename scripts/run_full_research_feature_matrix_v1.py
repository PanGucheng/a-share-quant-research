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
from research_validation.feature_matrix import atomic_parquet, canonical_hash, file_sha256, filter_to_pit_intervals, resumable_batch_valid  # noqa: E402
from research_validation.lineage import capture_code_state, load_artifact_manifest, write_stage_artifact_manifest  # noqa: E402
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


def load_raw(config: dict[str, object], symbols: list[str], runtime: Path, D: object) -> pd.DataFrame:
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
    wrapper = import_ta_wrapper(source_path)
    renamed = raw.rename(columns={"$open": "open", "$high": "high", "$low": "low", "$close": "close", "$volume": "volume"})
    rows = []
    for instrument, group in renamed.groupby("instrument", sort=True):
        source = group[["datetime", "instrument", "open", "high", "low", "close", "volume"]].sort_values("datetime").copy()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            computed = wrapper(source, open="open", high="high", low="low", close="close", volume="volume", fillna=False, colprefix="ta_", vectorized=False)
        missing = sorted(set(names) - set(computed.columns))
        if missing:
            raise ValueError(f"TA wrapper missing selected factors: {missing}")
        rows.append(computed[["datetime", "instrument", *names]])
    return pd.concat(rows, ignore_index=True)


def alpha101_batch(raw: pd.DataFrame, names: list[str], config: dict[str, object], output: Path) -> pd.DataFrame:
    source_config = Alpha101SourceConfig(
        provider_uri=str(resolve(config["provider_uri"])), market="point_in_time", start=str(config["warmup_start_date"]), end=str(config["end_date"]), max_instruments=None,
        source_local_path=resolve(config["alpha101_source_path"]), source_commit="d4b9e61f729df347730aa921b539b9df3c3fe36d", source_file="tests/KunTestUtil/ref_alpha101.py", source_module="KunTestUtil.ref_alpha101.Alphas", license="Apache-2.0",
        selected_smoke_factors=tuple(names), metadata_catalog=resolve(config["alpha101_metadata_catalog"]), catalog_stage="full_research_trial", catalog_enabled=True, catalog_runnable=True,
        labels=("label_10d_t1", "label_20d_t1"), output_dir=output,
    )
    return compute_alpha101_features(source_config, raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a resumable partitioned full-research factor matrix.")
    parser.add_argument("--config", type=Path, default=Path("configs/full_research_feature_matrix_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    catalog_manifest = load_artifact_manifest(resolve(config["factor_catalog_manifest"]))
    universe_manifest = load_artifact_manifest(resolve(config["universe_manifest"]))
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
    raw: pd.DataFrame | None = None
    batch_rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    for batch_id in ["alpha158", "alpha360", "project_basic", "ta", "alpha101"]:
        names = sorted(by_source.get(batch_id, []))
        path = runtime / f"{batch_id}.parquet"
        input_hash = canonical_hash({"batch": batch_id, "factors": names, "catalog": catalog_manifest["artifact_id"], "universe": universe_manifest["artifact_id"], "start": config["start_date"], "end": config["end_date"]})
        prior = previous.get(batch_id, {})
        attempts = int(prior.get("attempts", 0))
        if resumable_batch_valid(prior, input_hash, path):
            batch_rows.append({**prior, "cache_hit": True})
            continue
        started = time.perf_counter()
        attempts += 1
        try:
            if batch_id == "alpha158": frame = expression_batch(symbols, names, resolve(config["alpha158_inventory"]), config["start_date"], config["end_date"], D)
            elif batch_id == "alpha360": frame = expression_batch(symbols, names, resolve(config["alpha360_inventory"]), config["start_date"], config["end_date"], D)
            else:
                if raw is None: raw = load_raw(config, symbols, runtime, D)
                if batch_id == "project_basic": frame = add_basic_factors(raw.copy())[["datetime", "instrument", *names]]
                elif batch_id == "ta": frame = ta_batch(raw, names, resolve(config["ta_source_path"]))
                else: frame = alpha101_batch(raw, names, config, runtime)
            frame = frame.loc[pd.to_datetime(frame["datetime"]).between(pd.Timestamp(config["start_date"]), pd.Timestamp(config["end_date"]))]
            frame = filter_to_pit_intervals(frame, intervals)
            atomic_parquet(frame, path)
            row = {"batch_id": batch_id, "status": "pass", "factor_count": len(names), "row_count": len(frame), "instrument_count": frame["instrument"].nunique(), "start_date": frame["datetime"].min(), "end_date": frame["datetime"].max(), "input_hash": input_hash, "output_path": path.as_posix(), "output_sha256": file_sha256(path), "attempts": attempts, "runtime_seconds": time.perf_counter() - started, "cache_hit": False, "error": ""}
        except Exception as exc:
            row = {"batch_id": batch_id, "status": "failed", "factor_count": len(names), "row_count": 0, "instrument_count": 0, "start_date": "", "end_date": "", "input_hash": input_hash, "output_path": path.as_posix(), "output_sha256": "", "attempts": attempts, "runtime_seconds": time.perf_counter() - started, "cache_hit": False, "error": f"{type(exc).__name__}: {exc}"}
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
        contract_row("factor_catalog_count", len(entries) == 80, len(entries), 80),
        contract_row("all_batches_pass", failures == [], len(failures), 0),
        contract_row("all_factors_materialized", factor_count == len(entries), factor_count, len(entries)),
        contract_row("pit_universe_applied", bool(not success.empty and success["row_count"].gt(0).all()), universe_manifest["universe_artifact_id"], "nonempty PIT-filtered batches"),
        contract_row("batch_output_hashes_present", bool(not success.empty and success["output_sha256"].astype(str).str.len().eq(64).all()), int(success["output_sha256"].astype(str).str.len().eq(64).sum()), len(success)),
        contract_row("resume_metadata_present", set(["input_hash", "attempts", "cache_hit"]).issubset(batch.columns), list(batch.columns), "input_hash/attempts/cache_hit"),
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
        publisher.path("schema.json").write_text(json.dumps({"keys": ["datetime", "instrument"], "factors": sorted(entry.name for entry in entries), "partitioning": "source adapter", "runtime_committed": False}, indent=2) + "\n", encoding="utf-8")
        publisher.path("factor_matrix_report.md").write_text(f"# Full-Research Feature Matrix V1\n\n- Status: `{'pass' if ready else 'blocked'}`\n- Factors: `{factor_count}` / `{len(entries)}`\n- PIT instruments in source intervals: `{len(symbols)}`\n- Passed batches: `{len(success)}` / `{len(batch)}`\n- Runtime partitions are hash-addressed and intentionally excluded from Git.\n", encoding="utf-8")
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        factor_frame_id = "factor-frame:" + canonical_hash(success[["batch_id", "output_sha256"]].to_dict("records"))
        write_stage_artifact_manifest(project_root=PROJECT_ROOT, stage_id="full_research_feature_matrix_v1", config=config, output_dir=publisher.staging_dir, output_files=files, code_state=code_state, input_manifest_paths=[resolve(config["factor_catalog_manifest"]), resolve(config["universe_manifest"])], factor_frame_id=factor_frame_id, start_date=config["start_date"], end_date=config["end_date"], lineage_status="complete", artifact_status="pass" if ready else "blocked", blocked_reason="" if ready else "blocked_feature_matrix_batch_failure")
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
