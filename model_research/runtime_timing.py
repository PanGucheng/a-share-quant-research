from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import pandas as pd


RUNTIME_TIMING_COLUMNS = [
    "stage",
    "execution_class",
    "execution_profile",
    "outer_split_id",
    "policy_id",
    "fold",
    "batch_index",
    "structural_row_id",
    "candidate_sha256",
    "boosting_round",
    "feature_count",
    "train_rows",
    "validation_rows",
    "output_rows",
    "wall_seconds",
    "cpu_seconds",
    "cpu_core_equivalent",
    "read_bytes",
    "write_bytes",
    "rss_before_mib",
    "rss_after_mib",
    "peak_rss_mib",
    "execution_dtype",
    "thread_count",
    "cache_hit",
    "dataset_identity_sha256",
]


def _current_rss_mib() -> float:
    try:
        import psutil

        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except Exception:  # pragma: no cover - optional resource diagnostic
        return float("nan")


def _current_io_bytes() -> tuple[int | None, int | None]:
    try:
        import psutil

        counters = psutil.Process(os.getpid()).io_counters()
        return int(counters.read_bytes), int(counters.write_bytes)
    except Exception:  # pragma: no cover - optional resource diagnostic
        return None, None


class RuntimeTimingRecorder:
    """Low-overhead wall/CPU/RSS timing rows for research runtime artifacts."""

    def __init__(self, **base_fields: Any) -> None:
        self._base_fields = dict(base_fields)
        self._rows: list[dict[str, Any]] = []

    @contextmanager
    def measure(self, stage: str, **fields: Any) -> Iterator[dict[str, Any]]:
        payload = {**self._base_fields, **fields}
        rss_before = _current_rss_mib()
        read_before, write_before = _current_io_bytes()
        wall_started = time.perf_counter()
        cpu_started = time.process_time()
        try:
            yield payload
        finally:
            rss_after = _current_rss_mib()
            read_after, write_after = _current_io_bytes()
            wall_seconds = time.perf_counter() - wall_started
            cpu_seconds = time.process_time() - cpu_started
            payload.update(
                {
                    "stage": stage,
                    "wall_seconds": wall_seconds,
                    "cpu_seconds": cpu_seconds,
                    "cpu_core_equivalent": (
                        cpu_seconds / wall_seconds if wall_seconds > 0 else 0.0
                    ),
                    "read_bytes": (
                        read_after - read_before
                        if read_after is not None and read_before is not None
                        else None
                    ),
                    "write_bytes": (
                        write_after - write_before
                        if write_after is not None and write_before is not None
                        else None
                    ),
                    "rss_before_mib": rss_before,
                    "rss_after_mib": rss_after,
                    "peak_rss_mib": max(rss_before, rss_after),
                }
            )
            self._rows.append(payload)

    def frame(self) -> pd.DataFrame:
        frame = pd.DataFrame(self._rows)
        for column in RUNTIME_TIMING_COLUMNS:
            if column not in frame:
                frame[column] = pd.NA
        extra = [column for column in frame.columns if column not in RUNTIME_TIMING_COLUMNS]
        return frame[[*RUNTIME_TIMING_COLUMNS, *extra]]

    def write_csv(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.frame().to_csv(path, index=False)
