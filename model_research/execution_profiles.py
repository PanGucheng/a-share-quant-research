from __future__ import annotations

import copy
import os
from typing import Any


THREAD_ENVIRONMENT_VARIABLES = (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)


def with_lightgbm_threads(
    frozen_config: dict[str, Any], num_threads: int
) -> dict[str, Any]:
    """Return an execution-only clone of a validated frozen LightGBM config."""
    if isinstance(num_threads, bool) or int(num_threads) < 1:
        raise ValueError("LightGBM execution threads must be a positive integer")
    cloned = copy.deepcopy(frozen_config)
    cloned["determinism"]["num_threads"] = int(num_threads)
    cloned["resources"]["threads"] = int(num_threads)
    return cloned


def thread_environment() -> dict[str, str | None]:
    return {name: os.environ.get(name) for name in THREAD_ENVIRONMENT_VARIABLES}


def normalized_thread_environment(num_threads: int) -> dict[str, str]:
    """Environment policy for an isolated worker with one LightGBM task."""
    if isinstance(num_threads, bool) or int(num_threads) < 1:
        raise ValueError("worker thread budget must be a positive integer")
    return {name: str(int(num_threads)) for name in THREAD_ENVIRONMENT_VARIABLES}
