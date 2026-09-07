"""Resumable 765-factor primary computation; stop before candidate-rule freeze."""

# ruff: noqa: E402 -- initialize numerical thread limits before importing pandas.
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import pandas as pd
import numpy as np
import yaml

from factor_research.long_history_screening import (
    KEYS, LABEL, bounded_price_cache, common_samples, development_calendar,
    exact_primary_labels, frame_hash, label_map, native_primary_smoke, preflight,
    primary_fdr, read_factor, sha256_file, summarize_daily_metrics,
)
from qlib_baseline.io import atomic_write_json
from qlib_baseline.settings import load_settings
from research_validation.canonical_dataset import canonical_hash
from scripts.run_long_history_multi_evaluator_screening_v1 import native_modules

PROFILE = "ce3d1c0cf946be1179d117f9726409faeabc32839741e30c073a2fd0ba0d41bc"


@contextmanager
def run_lock(path):
    """OS lock is released even on abrupt process death; never delete the lock file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def bind_contract(out, contract):
    path = out / "contract.json"
    # Compare JSON-normalized data, including paths/timestamps.
    normalized = json.loads(json.dumps(contract, default=str))
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != normalized:
            raise ValueError("run contract changed; preserve this run and use a new run-id")
    else:
        if (out / "chunks").exists():
            raise ValueError("chunks exist without their run contract")
        atomic_write_json(path, normalized)
    return canonical_hash(normalized)


def completed_chunk(folder, contract_hash):
    if not folder.exists():
        return None
    receipt = json.loads((folder / "receipt.json").read_text(encoding="utf-8"))
    if receipt["contract_hash"] != contract_hash or receipt["execution_status"] != "complete":
        raise ValueError(f"invalid completed chunk: {folder}")
    expected = receipt["file_hashes"]
    actual = {p.name for p in folder.iterdir() if p.is_file() and p.name != "receipt.json"}
    if actual != set(expected) or any(sha256_file(folder / n) != h for n, h in expected.items()):
        raise ValueError(f"completed chunk corrupted: {folder}; preserve and explicitly rebuild")
    return receipt


def publish_chunk(staging, target, receipt, contract_hash):
    receipt = {**receipt, "contract_hash": contract_hash, "execution_status": "complete"}
    receipt["file_hashes"] = {p.name: sha256_file(p) for p in staging.iterdir() if p.is_file()}
    atomic_write_json(staging / "receipt.json", receipt)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging.rename(target)
    return receipt


def aggregate(out, inventory, calendar, config, contract_hash):
    """Read only verified completed chunks; missing jobs never become undefined tests."""
    summaries, rank_ic, jobs = [], {}, []
    dates = label_map(calendar)
    for factor in inventory.loc[inventory.research_usable, "factor"]:
        collected = {}
        for year in range(2010, 2024):
            folder = out / "chunks" / str(year) / factor
            receipt = completed_chunk(folder, contract_hash)
            if receipt is None:
                raise ValueError(f"missing required job: {year}/{factor}")
            jobs.append({"factor": factor, "year": year, **receipt})
            for name in receipt["file_hashes"]:
                if not name.endswith(".parquet"):
                    continue
                raw = pd.read_parquet(folder / name)
                metric = Path(name).stem
                if metric == "alphalens_quantile":
                    wide = raw.iloc[:, 0].unstack("factor_quantile")
                    for quantile in range(1, 6):
                        collected.setdefault(f"alphalens_q{quantile}", []).append(wide[quantile])
                    collected.setdefault("alphalens_q5_minus_q1", []).append(wide[5] - wide[1])
                else:
                    # Alphalens calendar padding may overlap an adjacent year;
                    # it is empty by the verified native parity contract.
                    collected.setdefault(metric, []).append(raw.iloc[:, 0].dropna())
        empty = pd.Series(dtype=float, index=pd.DatetimeIndex([]))
        rank_ic[factor] = pd.concat(collected["qlib_ic"]) if "qlib_ic" in collected else empty
        required = ["alphalens_ic", "jqfactor_ic", "qlib_ic", "qlib_pearson",
                    "jqfactor_returns", "qlib_long_short", "qlib_cross_section_mean",
                    *[f"alphalens_q{i}" for i in range(1, 6)], "alphalens_q5_minus_q1"]
        for metric in required:
            series = pd.concat(collected[metric]) if metric in collected else empty
            summary = summarize_daily_metrics(series, dates, config["signal_eras"])
            summary["factor"], summary["metric"] = factor, metric
            summary["backend"] = metric.split("_")[0]
            summaries.append(summary)
    stage = out / "staging" / f"aggregate-{uuid.uuid4().hex}"
    stage.mkdir(parents=True)
    metrics = pd.concat(summaries, ignore_index=True)
    metrics["label"], metrics["universe"] = LABEL, config["universe"]
    metrics.to_parquet(stage / "period_metrics.parquet", index=False)
    metrics.to_csv(stage / "period_metrics.csv", index=False)
    print("All 10,710 chunks verified; computing the single 765-factor bootstrap/FDR family", flush=True)
    bootstrap = config["bootstrap"]
    fdr = primary_fdr(inventory, rank_ic, calendar, samples=bootstrap["samples"],
                      block_length=bootstrap["block_length"], seed=bootstrap["seed"])
    fdr.to_csv(stage / "primary_fdr.csv", index=False)
    inventory.to_csv(stage / "factor_inventory.csv", index=False)
    atomic_write_json(stage / "job_receipts.json", {"jobs": jobs})
    return publish_chunk(stage, out / "aggregate", {
        "scope": "primary raw metrics and FDR; Evidence/Candidate Board review pending",
        "candidate_status": "not_evaluated", "completed_chunks": len(jobs),
        "held_aside_recent_diagnostic_accessed": False,
    }, contract_hash)


def run_full(config, out, max_new_jobs=None, rebuild_chunk=None):
    out.mkdir(parents=True, exist_ok=True)
    with run_lock(out / "run.lock"):
        settings = load_settings(project_root=ROOT)
        if settings.qlib_provider is None:
            raise ValueError("configure qlib_provider")
        if settings.qlib_source:
            sys.path.insert(0, str(settings.qlib_source))
        frozen = yaml.safe_load((ROOT / "configs/long_history_multi_evaluator_screening_v1.yaml").read_text())
        if config != frozen:
            raise ValueError("full execution requires the qualified fixed config")
        inventory, partitions, identity = preflight(ROOT, config)
        calendar = development_calendar(settings.qlib_provider / "calendars/day.txt")
        modules, provenance = native_modules()
        profile_path = ROOT / "artifacts/long_history_multi_evaluator_screening_v1" / PROFILE / "native_profile.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        if provenance != profile["native_provenance"]:
            raise ValueError("native source/dependency drift from qualified profile")
        print("Binding input metadata and price content for resumable execution", flush=True)
        # Canonical parent bytes remain covered by inherited assembly certification.
        # Stat binding detects ordinary source replacement without re-reading all large parents.
        parents = {str(p): {"size": p.stat().st_size, "mtime_ns": p.stat().st_mtime_ns}
                   for p in map(Path, partitions.partition_path.unique())}
        price_sources = {str(p.relative_to(settings.qlib_provider)): sha256_file(p)
                         for p in sorted((settings.qlib_provider / "features").glob("*/close.day.bin"))}
        if not price_sources:
            raise ValueError("no provider close sources")
        contract = {
            "config": config, "identity": identity, "native_provenance": provenance,
            "profile_sha256": sha256_file(profile_path), "canonical_parent_stats": parents,
            "provider": str(settings.qlib_provider), "price_sources": price_sources,
            "calendar_sha256": sha256_file(settings.qlib_provider / "calendars/day.txt"),
            "implementation_hashes": {name: sha256_file(ROOT / name) for name in (
                "scripts/run_long_history_primary_full.py", "factor_research/long_history_screening.py",
                "scripts/run_long_history_multi_evaluator_screening_v1.py", "research_validation/labels.py",
                "research_validation/canonical_dataset.py", "research_validation/bootstrap.py",
                "research_validation/multiple_testing.py", "qlib_baseline/cache.py", "qlib_baseline/io.py")},
            "qualification_hashes": {name: sha256_file(ROOT / "reports/long_history_multi_evaluator_screening_v1" / name)
                                     for name in ("FEATURE_QUALITY_SUMMARY.json", "FEATURE_QUALITY_FULL.csv",
                                                  "PIT_SAMPLE_AUDIT.json", "BLOCK_EQUIVALENCE.csv")},
        }
        contract_hash = bind_contract(out, contract)
        if rebuild_chunk is not None:
            year, factor = rebuild_chunk.split("/")
            if year not in map(str, range(2010, 2024)) or factor not in set(inventory.loc[inventory.research_usable, "factor"]):
                raise ValueError("rebuild-chunk must name an exact planned year/factor")
            target = out / "chunks" / year / factor
            if not target.is_dir():
                raise ValueError("rebuild target does not exist")
            # Preserve damaged evidence and any dependent aggregate, never delete.
            archive = out / "preserved" / uuid.uuid4().hex
            archive.mkdir(parents=True)
            # Invalidate dependent aggregation first: interruption between the
            # two renames must not leave an old aggregate alongside a new chunk.
            if (out / "aggregate").exists():
                (out / "aggregate").rename(archive / "aggregate")
            target.rename(archive / f"{year}-{factor}")
            atomic_write_json(archive / "rebuild.json", {"requested_chunk": rebuild_chunk})
        import qlib
        from qlib.config import C, REG_CN
        from qlib.data import D
        qlib.init(provider_uri=str(settings.qlib_provider), region=REG_CN)
        C.kernels, C.joblib_backend = 1, "sequential"
        dates = label_map(calendar).dropna(subset=["exit_date"])
        completed, newly_done = 0, 0
        status = {"primary_mvp_status": "in_progress", "total_chunks": 765 * 14,
                  "pid": os.getpid(), "contract_hash": contract_hash,
                  "held_aside_recent_diagnostic_accessed": False}

        def progress(state, **extra):
            status.update(execution_status=state, completed_chunks=completed,
                          newly_completed_chunks=newly_done, updated_at=pd.Timestamp.now().isoformat(), **extra)
            atomic_write_json(out / "status.json", status)

        try:
            progress("running")
            for year in range(2010, 2024):
                mapping = dates.loc[dates.datetime.dt.year == year]
                shared_key_hash, shared_labels, price_audit = None, None, None
                for factor in inventory.loc[inventory.research_usable, "factor"]:
                    target = out / "chunks" / str(year) / factor
                    if completed_chunk(target, contract_hash) is not None:
                        completed += 1
                        continue
                    if max_new_jobs is not None and newly_done >= max_new_jobs:
                        progress("paused_job_limit", current_job=None)
                        return status
                    job = f"{year}/{factor}"
                    progress("running", current_job=job)
                    print(f"[{completed}/{765 * 14}] {job}", flush=True)
                    tick, access = time.perf_counter(), []
                    values = read_factor(partitions, factor, mapping.datetime.min(), mapping.datetime.max(), access=access)
                    if not values.datetime.isin(mapping.datetime).all():
                        raise ValueError("factor contains non-signal dates")
                    key_hash = frame_hash(values[KEYS])
                    if key_hash != shared_key_hash:
                        def loader(symbols, left, right):
                            return D.features(symbols, ["$close"], start_time=left, end_time=right, freq="day").reset_index()
                        prices, cache_status = bounded_price_cache(
                            settings.qlib_provider, sorted(values.instrument.unique()),
                            mapping.entry_date.min(), mapping.exit_date.max(),
                            ROOT / "tmp/long_history_multi_evaluator_screening_v1/prices", loader)
                        shared_labels = exact_primary_labels(values[KEYS], prices, calendar)
                        price_audit = {"requested_start": mapping.entry_date.min(), "requested_end": mapping.exit_date.max(),
                                       "slice_hash": frame_hash(prices), "cache_status": cache_status,
                                       "label_hash": frame_hash(shared_labels)}
                        shared_key_hash = key_hash
                        del prices
                    merged = values.merge(shared_labels[[*KEYS, LABEL]], on=KEYS, validate="one_to_one")
                    ic, quantile, masks = common_samples(merged, factor, min_count=config["min_count"])
                    if ic.empty:
                        results, receipt = {}, {"parity_status": "unavailable", "native_status": {},
                                               "reason": "no_definable_daily_samples"}
                    else:
                        results, receipt = native_primary_smoke(ic, quantile, modules, atol=config["parity_atol"])
                    if any(value.startswith("failed:") for value in receipt["native_status"].values()):
                        raise ValueError(f"required native metric failed: {receipt}")
                    if "alphalens_quantile" in results:
                        raw = results["alphalens_quantile"]
                        wide = raw.iloc[:, 0].unstack("factor_quantile")
                        expected_dates = pd.DatetimeIndex(quantile.datetime.unique()).sort_values()
                        if (set(wide.columns) != set(range(1, 6))
                                or not wide.index.equals(expected_dates)
                                or not np.isfinite(wide.to_numpy()).all()):
                            raise ValueError("required quantile output lost bins/dates or produced nonfinite values")
                    stage = out / "staging" / uuid.uuid4().hex
                    stage.mkdir(parents=True)
                    masks.to_csv(stage / "daily_sample_status.csv", index=False)
                    atomic_write_json(stage / "access.json", {"factor": access, "price": price_audit})
                    for name, result in results.items():
                        if isinstance(result, pd.Series):
                            result = result.to_frame(name=name)
                        result.to_parquet(stage / f"{name}.parquet")
                    publish_chunk(stage, target, {**receipt, "factor": factor, "year": year,
                                  "signal_start": mapping.datetime.min(), "signal_end": mapping.datetime.max(),
                                  "max_label_exit_date": mapping.exit_date.max(), "factor_hash": frame_hash(values),
                                  "key_hash": key_hash, "candidate_status": "not_evaluated",
                                  "wall_seconds": time.perf_counter() - tick}, contract_hash)
                    completed += 1
                    newly_done += 1
                    progress("running")
            progress("aggregating", current_job="primary_fdr_and_period_metrics")
            if completed_chunk(out / "aggregate", contract_hash) is None:
                aggregate(out, inventory, calendar, config, contract_hash)
            progress("computation_complete_review_pending", current_job=None)
            return status
        except BaseException as exc:
            progress("interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                     error=f"{type(exc).__name__}: {exc}")
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-new-jobs", type=int, help="Pause after this many new chunks; same command without limit resumes")
    parser.add_argument("--rebuild-chunk", help="Explicitly preserve and rebuild one completed year/factor chunk")
    args = parser.parse_args()
    if not args.run_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in args.run_id):
        parser.error("invalid run-id")
    if args.max_new_jobs is not None and args.max_new_jobs < 1:
        parser.error("max-new-jobs must be positive")
    if args.rebuild_chunk is not None and args.rebuild_chunk.count("/") != 1:
        parser.error("rebuild-chunk requires year/factor")
    config = yaml.safe_load((ROOT / "configs/long_history_multi_evaluator_screening_v1.yaml").read_text())
    result = run_full(config, ROOT / "outputs/long_history_multi_evaluator_screening_v1" / args.run_id,
                      args.max_new_jobs, args.rebuild_chunk)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
