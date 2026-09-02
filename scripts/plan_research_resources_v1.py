from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import psutil

from model_research.protocol import PROJECT_ROOT
from model_research.resource_scheduler import (
    ResourceBudget,
    WorkloadClass,
    candidate_worker_thread_plans,
)


def _resolve(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate CPU-and-RAM-safe worker/thread benchmark combinations"
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--reserved-ram-mib", type=float, default=4096.0)
    parser.add_argument("--light-rss-mib", type=float, default=4096.0)
    parser.add_argument("--medium-rss-mib", type=float, default=8192.0)
    parser.add_argument("--broad-rss-mib", type=float, default=17408.0)
    parser.add_argument("--thread-counts", type=int, nargs="+", default=[1, 2, 4, 8])
    args = parser.parse_args()
    output_dir = _resolve(args.output_dir)
    if output_dir.exists():
        raise FileExistsError("resource plan output is immutable")
    output_dir.mkdir(parents=True, exist_ok=False)
    budget = ResourceBudget(
        physical_cores=int(psutil.cpu_count(logical=False) or 1),
        logical_cores=int(psutil.cpu_count(logical=True) or 1),
        available_ram_mib=float(psutil.virtual_memory().available / 1024**2),
        reserved_ram_mib=float(args.reserved_ram_mib),
    )
    workloads = (
        WorkloadClass("light", float(args.light_rss_mib)),
        WorkloadClass("medium", float(args.medium_rss_mib)),
        WorkloadClass("broad", float(args.broad_rss_mib)),
    )
    rows = [
        plan.to_dict()
        for workload in workloads
        for plan in candidate_worker_thread_plans(
            budget, workload, thread_candidates=args.thread_counts
        )
    ]
    pd.DataFrame(rows).to_csv(output_dir / "worker_thread_candidates.csv", index=False)
    manifest = {
        "schema_version": 1,
        "purpose": "benchmark_candidates_not_authorization",
        "budget": budget.__dict__,
        "workloads": [value.__dict__ for value in workloads],
        "oversubscription_forbidden": True,
        "candidate_count": len(rows),
    }
    (output_dir / "resource_budget.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
