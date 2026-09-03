from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class ResourceBudget:
    physical_cores: int
    logical_cores: int
    available_ram_mib: float
    reserved_ram_mib: float = 2048.0


@dataclass(frozen=True)
class WorkloadClass:
    name: str
    peak_rss_mib_per_worker: float
    minimum_threads_per_worker: int = 1


@dataclass(frozen=True)
class WorkerThreadPlan:
    workload_class: str
    workers: int
    threads_per_worker: int
    cpu_threads_reserved: int
    ram_mib_reserved: float
    cpu_budget_valid: bool
    ram_budget_valid: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def candidate_worker_thread_plans(
    budget: ResourceBudget,
    workload: WorkloadClass,
    *,
    thread_candidates: Iterable[int] = (1, 2, 4, 8),
) -> list[WorkerThreadPlan]:
    if budget.physical_cores < 1 or budget.logical_cores < budget.physical_cores:
        raise ValueError("invalid CPU budget")
    usable_ram = budget.available_ram_mib - budget.reserved_ram_mib
    if usable_ram <= 0 or workload.peak_rss_mib_per_worker <= 0:
        raise ValueError("invalid RAM budget")
    max_ram_workers = int(
        math.floor(usable_ram / workload.peak_rss_mib_per_worker)
    )
    if max_ram_workers < 1:
        return []
    plans: list[WorkerThreadPlan] = []
    seen: set[tuple[int, int]] = set()
    for threads in sorted({int(value) for value in thread_candidates}):
        if threads < workload.minimum_threads_per_worker or threads > budget.physical_cores:
            continue
        max_cpu_workers = max(1, budget.physical_cores // threads)
        for workers in range(1, min(max_cpu_workers, max_ram_workers) + 1):
            key = (workers, threads)
            if key in seen:
                continue
            seen.add(key)
            cpu_reserved = workers * threads
            ram_reserved = workers * workload.peak_rss_mib_per_worker
            plans.append(
                WorkerThreadPlan(
                    workload_class=workload.name,
                    workers=workers,
                    threads_per_worker=threads,
                    cpu_threads_reserved=cpu_reserved,
                    ram_mib_reserved=ram_reserved,
                    cpu_budget_valid=cpu_reserved <= budget.physical_cores,
                    ram_budget_valid=ram_reserved <= usable_ram,
                )
            )
    return sorted(
        plans,
        key=lambda row: (
            -row.cpu_threads_reserved,
            row.ram_mib_reserved,
            row.workers,
        ),
    )


def workload_classes_from_evidence(
    evidence: pd.DataFrame,
    *,
    profile_id: str,
    safety_multiplier: float = 1.15,
) -> list[WorkloadClass]:
    required = {"profile_id", "policy_id", "peak_rss_mib"}
    if not required.issubset(evidence.columns):
        raise ValueError("resource evidence is missing required columns")
    if safety_multiplier < 1.0:
        raise ValueError("resource evidence safety multiplier cannot be below one")
    selected = evidence.loc[evidence["profile_id"].astype(str).eq(profile_id)].copy()
    if selected.empty:
        raise ValueError("resource evidence does not contain the requested profile")
    selected["peak_rss_mib"] = pd.to_numeric(selected["peak_rss_mib"], errors="raise")
    rows = []
    for policy_id, group in selected.groupby("policy_id", sort=True):
        peak = float(group["peak_rss_mib"].max())
        if not math.isfinite(peak) or peak <= 0:
            raise ValueError("resource evidence contains invalid peak RSS")
        rows.append(
            WorkloadClass(
                name=str(policy_id),
                peak_rss_mib_per_worker=peak * safety_multiplier,
            )
        )
    return rows
