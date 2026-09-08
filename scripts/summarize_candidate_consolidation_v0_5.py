"""Verify daily evidence and publish resumable, exact Full/Era/LOO statistics."""
# ruff: noqa: E402
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_candidate_consolidation_v0_5 import completed_chunk, run_lock
from factor_research.candidate_consolidation import verify_primary
from factor_research.candidate_consolidation_summary import reduce_pairs, view_masks
from factor_research.long_history_screening import sha256_file
from qlib_baseline.io import atomic_write_json
from research_validation.canonical_dataset import canonical_hash
import numpy as np
import pandas as pd


def verify_daily(out):
    contract = json.loads((out / "contract.json").read_text())
    digest = canonical_hash(contract)
    calendar = pd.DatetimeIndex(contract["dates"])
    names = contract["factor_axis"]
    if len(names) != 494 or names != sorted(set(names)) or len(calendar) != 3382:
        raise ValueError("unexpected working set or date scope")
    if calendar.min() != pd.Timestamp("2010-01-29") or calendar.max() != pd.Timestamp("2023-12-29") or calendar.has_duplicates:
        raise ValueError("invalid date boundary")
    folders, receipts, arrays = [], [], []
    for month, days in pd.Series(calendar, index=calendar).groupby(calendar.to_period("M")):
        folder = out / "daily" / str(month)
        receipt = completed_chunk(folder, digest)
        if receipt is None or receipt["dates"] != [str(d.date()) for d in days]:
            raise ValueError(f"missing/inconsistent dated chunk {month}")
        data = {field: np.load(folder / (field + ".npy"), mmap_mode="r", allow_pickle=False)
                for field in ("rho", "n_common", "reason", "finite_count", "infinite_count", "universe_count")}
        pairs = len(names) * (len(names)-1) // 2
        for field in ("rho", "n_common", "reason"):
            if data[field].shape != (len(days), pairs):
                raise ValueError("daily pair schema mismatch")
        for field in ("finite_count", "infinite_count"):
            if data[field].shape != (len(days), len(names)):
                raise ValueError("daily factor schema mismatch")
        if data["universe_count"].shape != (len(days),):
            raise ValueError("daily universe schema mismatch")
        arrays.append(data); folders.append(folder); receipts.append(receipt)
    return contract, calendar, folders, receipts, arrays


def run(out):
    target = out / "summary_v1"
    with run_lock(target / "run.lock"):
        verify_primary(ROOT)
        print("Verifying all 168 daily chunks and hashes", flush=True)
        contract, dates, folders, receipts, arrays = verify_daily(out)
        binding = {"daily_contract_hash": canonical_hash(contract),
                   "receipts": {p.name: sha256_file(p / "receipt.json") for p in folders},
                   "code": {p: sha256_file(ROOT / p) for p in (
                       "factor_research/candidate_consolidation_summary.py", "scripts/summarize_candidate_consolidation_v0_5.py")},
                   "pair_block_size": 1024, "versions": {"numpy": np.__version__, "pandas": pd.__version__}}
        path = target / "contract.json"
        if path.exists() and json.loads(path.read_text()) != binding:
            raise ValueError("summary implementation/input changed; preserve existing summary")
        atomic_write_json(path, binding)
        digest = canonical_hash(binding)
        i, j = np.triu_indices(len(contract["factor_axis"]), 1)
        finite = np.concatenate([a["finite_count"] for a in arrays])
        universe = np.concatenate([a["universe_count"] for a in arrays])
        masks = view_masks(dates)
        started = time.perf_counter()
        for offset in range(0, len(i), 1024):
            end = min(offset + 1024, len(i))
            key = f"{offset:06d}_{end:06d}"
            folder = target / "blocks" / key
            if completed_chunk(folder, digest):
                continue
            rho, common, reason = [np.concatenate([a[field][:, offset:end] for a in arrays])
                                   for field in ("rho", "n_common", "reason")]
            frames = []
            for view, mask in masks.items():
                table = reduce_pairs(rho[mask], common[mask], reason[mask],
                                     finite[mask][:, i[offset:end]], finite[mask][:, j[offset:end]], universe[mask],
                                     minimum_fraction=contract["config"]["diagnostics"]["valid_date_fraction"],
                                     minimum_coverage=contract["config"]["diagnostics"]["common_coverage_q10"])
                table.insert(0, "pair_id", np.arange(offset, end)); table.insert(0, "view", view)
                frames.append(table)
            staging = target / (".staging_" + uuid.uuid4().hex)
            staging.mkdir()
            pd.concat(frames, ignore_index=True).to_parquet(staging / "pairs.parquet", index=False)
            atomic_write_json(staging / "receipt.json", {"status": "complete", "contract_hash": digest,
                              "file_hashes": {"pairs.parquet": sha256_file(staging / "pairs.parquet")}})
            folder.parent.mkdir(parents=True, exist_ok=True); staging.rename(folder)
            atomic_write_json(target / "status.json", {"status": "running", "completed_pairs": end,
                              "total_pairs": len(i), "elapsed_seconds": time.perf_counter()-started})
            print(f"[{end}/{len(i)}] exact Full/Era/LOO reduction", flush=True)
        verify_primary(ROOT)
        atomic_write_json(target / "status.json", {"status": "complete", "pairs": len(i), "views": list(masks),
                          "dates": len(dates), "daily_chunks": len(receipts), "wall_seconds": time.perf_counter()-started})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.run_id):
        parser.error("invalid run-id")
    run(ROOT / "outputs/candidate_consolidation_v0_5" / args.run_id)
