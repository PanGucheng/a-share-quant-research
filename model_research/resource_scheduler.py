from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Iterable


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
