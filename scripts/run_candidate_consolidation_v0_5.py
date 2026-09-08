"""Bounded canary and resumable daily evidence. No model or label execution."""
# ruff: noqa: E402
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import multiprocessing
import os
from pathlib import Path
import re
import shutil
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"

import numpy as np
import pandas as pd
import psutil
import scipy
import yaml

from factor_research.candidate_consolidation import (
    canary_dates, exact_duplicate_groups, prepare_inputs, read_panel, verify_primary,
)
from factor_research.factor_similarity import daily_pairwise_spearman
from factor_research.long_history_screening import development_calendar, sha256_file
from qlib_baseline.io import atomic_write_json, atomic_output_path
from qlib_baseline.settings import load_settings
from research_validation.canonical_dataset import canonical_hash

STATE = {}
IMPLEMENTATION = ["factor_research/candidate_consolidation.py", "factor_research/factor_similarity.py",
                  "scripts/run_candidate_consolidation_v0_5.py", "research_validation/canonical_dataset.py",
                  "factor_research/long_history_screening.py", "model_research/feature_eligibility.py",
                  "factor_research/factor_clustering.py", "qlib_baseline/io.py"]


@contextmanager
def run_lock(path):
    """Same OS-lock pattern as the Primary runner; no imports of its label runner."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
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


def completed_chunk(folder, contract_hash):
    if not folder.exists():
        return None
    receipt = json.loads((folder / "receipt.json").read_text(encoding="utf-8"))
    if receipt.get("contract_hash") != contract_hash or receipt.get("status") != "complete":
        raise ValueError(f"invalid receipt: {folder}")
    files = {p.name for p in folder.iterdir() if p.is_file() and p.name != "receipt.json"}
    if files != set(receipt["file_hashes"]) or any(sha256_file(folder / f) != h for f, h in receipt["file_hashes"].items()):
        raise ValueError(f"corrupted chunk, preserve for diagnosis: {folder}")
    return receipt


def init_worker(partitions, factors, config, output, contract_hash, oracle):
    STATE.update(partitions=partitions, factors=factors, config=config, output=Path(output),
                 contract_hash=contract_hash, oracle=oracle)


def compute_job(job):
    key, days = job
    target = STATE["output"] / key
    with run_lock(STATE["output"] / "locks" / (key + ".lock")):
        previous = completed_chunk(target, STATE["contract_hash"])
        if previous:
            return previous
        started = time.perf_counter()
        access = []
        days = pd.DatetimeIndex(days)
        panel = read_panel(STATE["partitions"], STATE["factors"], days[0], days[-1], access=access)
        if not pd.DatetimeIndex(panel.datetime.unique()).equals(days):
            raise ValueError("canonical trading dates do not match scheduled dates")
        read_seconds = time.perf_counter() - started
        factors = STATE["factors"]
        pair_i, pair_j = np.triu_indices(len(factors), 1)
        daily = []
        max_error = 0.0
        kernel_seconds, oracle_seconds = 0.0, 0.0
        rss_peak = psutil.Process().memory_info().rss
        engines, mask_counts = [], []
        for day, frame in panel.groupby("datetime", sort=True):
            x = frame[factors].to_numpy(dtype=float)
            tick = time.perf_counter()
            result = daily_pairwise_spearman(x, STATE["config"]["minimum_pair_observations"], engine=STATE["config"]["engine"])
            kernel_seconds += time.perf_counter() - tick
            if STATE["oracle"]:
                tick = time.perf_counter()
                oracle = daily_pairwise_spearman(x, STATE["config"]["minimum_pair_observations"], engine="pandas")
                oracle_seconds += time.perf_counter() - tick
                np.testing.assert_allclose(result["rho"], oracle["rho"], rtol=0, atol=STATE["config"]["parity_atol"], equal_nan=True)
                np.testing.assert_array_equal(result["reason"], oracle["reason"])
                finite = np.isfinite(result["rho"])
                if finite.any():
                    max_error = max(max_error, float(np.max(np.abs(result["rho"][finite] - oracle["rho"][finite]))))
            daily.append({"rho": result["rho"][pair_i, pair_j], "n_common": result["n_common"][pair_i, pair_j],
                          "reason": result["reason"][pair_i, pair_j], "finite_count": result["finite_count"],
                          "infinite_count": result["infinite_count"], "universe_count": result["universe_count"]})
            engines.append(result["engine"])
            mask_counts.append(result["mask_groups"])
            rss_peak = max(rss_peak, psutil.Process().memory_info().rss)
        aliases = exact_duplicate_groups(panel, factors)
        staging = STATE["output"] / (".staging_" + key + "_" + uuid.uuid4().hex)
        staging.mkdir(parents=True)
        # Plain .npy enables memory-mapped pair-block aggregation without copying a full month.
        for field in daily[0]:
            np.save(staging / (field + ".npy"), np.asarray([d[field] for d in daily]), allow_pickle=False)
        atomic_write_json(staging / "access.json", {"slices": access})
        atomic_write_json(staging / "aliases.json", {"scope": key, "relations": aliases})
        receipt = {"status": "complete", "contract_hash": STATE["contract_hash"], "job": key,
                   "dates": [str(d.date()) for d in days], "rows": len(panel), "pid": os.getpid(),
                   "read_seconds": read_seconds, "wall_seconds": time.perf_counter() - started,
                   "kernel_seconds": kernel_seconds, "oracle_seconds": oracle_seconds,
                   "rss_peak_sampled_bytes": rss_peak, "mask_groups": mask_counts, "engines": engines,
                   "oracle_max_abs_error": max_error, "oracle_checked": STATE["oracle"],
                   "file_hashes": {p.name: sha256_file(p) for p in staging.iterdir()}}
        atomic_write_json(staging / "receipt.json", receipt)
        target.parent.mkdir(parents=True, exist_ok=True)
        staging.rename(target)
        return receipt


def execute(jobs, partitions, factors, config, output, contract_hash, workers, oracle=False):
    output.mkdir(parents=True, exist_ok=True)
    receipts, pending = [], []
    for job in jobs:
        receipt = completed_chunk(output / job[0], contract_hash)
        if receipt:
            receipts.append(receipt)
        else:
            pending.append(job)
    started = time.perf_counter()
    args = (partitions, factors, config, output, contract_hash, oracle)
    def record(receipt):
        receipts.append(receipt)
        elapsed = time.perf_counter() - started
        atomic_write_json(output / "status.json", {"status": "running", "completed_jobs": len(receipts),
            "total_jobs": len(jobs), "current_job": receipt["job"], "workers": workers,
            "pid": os.getpid(), "elapsed_seconds": elapsed, "updated_at": datetime.now(timezone.utc).isoformat()})
        print(f"[{len(receipts)}/{len(jobs)}] {receipt['job']} ({receipt['wall_seconds']:.1f}s, worker {receipt['pid']})", flush=True)
    try:
        if workers == 1:
            init_worker(*args)
            for job in pending:
                record(compute_job(job))
        else:
            with ProcessPoolExecutor(workers, mp_context=multiprocessing.get_context("spawn"),
                                     initializer=init_worker, initargs=args) as pool:
                futures = [pool.submit(compute_job, j) for j in pending]
                for future in as_completed(futures):
                    record(future.result())
    except BaseException as exc:
        atomic_write_json(output / "status.json", {"status": "interrupted_or_failed", "error": str(exc),
                                                   "completed_jobs": len(receipts), "total_jobs": len(jobs)})
        raise
    elapsed = time.perf_counter() - started
    atomic_write_json(output / "status.json", {"status": "daily_evidence_complete", "completed_jobs": len(receipts),
                                               "total_jobs": len(jobs), "new_jobs": len(pending), "wall_seconds": elapsed})
    return sorted(receipts, key=lambda r: r["job"]), elapsed, len(pending)


def run(config, out, stage, workers):
    with run_lock(out / "run.lock"):
        working, inventory, partitions, evidence = prepare_inputs(ROOT, config)
        calendar = development_calendar(load_settings().qlib_provider / "calendars/day.txt")
        factors = sorted(set(working.factor) | set(config["controls"]))
        contract = {"config": config, "evidence": evidence, "active_factors": list(working.factor),
                    "factor_axis": factors, "dates": [str(d.date()) for d in calendar],
                    "code_hashes": {p: sha256_file(ROOT / p) for p in IMPLEMENTATION},
                    "versions": {"numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__},
                    "schema": "upper_triangle_float64_rho_uint32_count_v1"}
        contract_hash = canonical_hash(contract)
        path = out / "contract.json"
        if path.exists() and json.loads(path.read_text(encoding="utf-8")) != contract:
            raise ValueError("contract changed; preserve this run and choose a new run-id")
        atomic_write_json(path, contract)
        for name, frame in (("working_set.csv", working), ("inventory_semantic_audit.csv", inventory)):
            with atomic_output_path(out / name) as temporary:
                frame.to_csv(temporary, index=False)
        if stage == "prepare":
            print(f"Prepared {len(working)} active / {len(inventory)} inventory; {len(factors)} columns including controls")
            return
        if stage == "canary":
            days = canary_dates(calendar)
            jobs = [(str(d.date()), [d]) for d in days]
            serial, t1, n1 = execute(jobs, partitions, factors, config, out / "canary_1", contract_hash, 1, True)
            parallel, t8, n8 = execute(jobs, partitions, factors, config, out / "canary_8", contract_hash, 8, True)
            for first, second in zip(serial, parallel, strict=True):
                for field in ("rho", "n_common", "reason", "finite_count", "infinite_count", "universe_count"):
                    a = np.load(out / "canary_1" / first["job"] / (field + ".npy"))
                    b = np.load(out / "canary_8" / second["job"] / (field + ".npy"))
                    np.testing.assert_array_equal(a, b)
            report = {"status": "pass", "contract_hash": contract_hash, "dates": [str(d.date()) for d in days],
                      "active_count": len(working), "column_count_including_controls": len(factors),
                      "one_vs_eight": "bitwise_equal_including_nan", "serial_wall_seconds": t1,
                      "parallel_wall_seconds": t8, "new_serial_jobs": n1, "new_parallel_jobs": n8,
                      "timings_include_oracle": True, "timings_valid_for_fresh_comparison": n1 == n8 == len(jobs),
                      "serial_kernel_seconds": sum(r["kernel_seconds"] for r in serial),
                      "serial_oracle_seconds": sum(r["oracle_seconds"] for r in serial),
                      "max_oracle_abs_error": max(r["oracle_max_abs_error"] for r in serial + parallel),
                      "largest_worker_rss_sampled_bytes": max(r["rss_peak_sampled_bytes"] for r in serial + parallel),
                      "full_eta_status": "requires_caution_single_day_io_and_oracle_overhead",
                      "held_aside_recent_diagnostic_accessed": False}
            verify_primary(ROOT)
            atomic_write_json(out / "CANARY.json", report)
            print(json.dumps(report, indent=2))
            return
        qualification = json.loads((out / "CANARY.json").read_text(encoding="utf-8"))
        if qualification["status"] != "pass" or qualification["contract_hash"] != contract_hash:
            raise ValueError("current contract has not passed canary")
        if shutil.disk_usage(out).free < 50 * 1024**3:
            raise ValueError("full daily evidence requires 50 GiB free disk reserve")
        jobs = [(str(month), list(group)) for month, group in pd.Series(calendar, index=calendar).groupby(calendar.to_period("M"))]
        execute(jobs, partitions, factors, config, out / "daily", contract_hash, workers)
        verify_primary(ROOT)
        atomic_write_json(out / "status.json", {"status": "daily_evidence_complete_aggregation_pending",
            "next": "Full/Era aggregation, clustering, exposure and representative proposal",
            "held_aside_recent_diagnostic_accessed": False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--stage", choices=["prepare", "canary", "full"], default="prepare")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.run_id) or not 1 <= args.workers <= 8:
        parser.error("safe run-id and workers 1..8 required")
    config = yaml.safe_load((ROOT / "configs/candidate_consolidation_v0_5.yaml").read_text(encoding="utf-8"))
    run(config, ROOT / "outputs/candidate_consolidation_v0_5" / args.run_id, args.stage, args.workers)


if __name__ == "__main__":
    main()
