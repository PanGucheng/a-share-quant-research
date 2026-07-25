from __future__ import annotations

import json
import os
import platform
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

from research_validation.feature_matrix import canonical_hash

from .schemas import PRE_TEST_FREEZE_REQUIRED_FIELDS, freeze_schema_missing


def _version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return "not_installed"


def capture_environment_lock(*, qlib_commit_sha: str) -> dict[str, Any]:
    try:
        import numpy as np

        blas = (
            getattr(np.__config__, "CONFIG", {})
            .get("Build Dependencies", {})
            .get("blas", {})
        )
        blas_backend = {
            "name": blas.get("name", "unresolved"),
            "version": blas.get("version", "unresolved"),
            "configuration": blas.get(
                "openblas configuration",
                blas.get("detection method", "unresolved"),
            ),
        }
    except Exception as exc:  # pragma: no cover - defensive environment audit
        blas_backend = {"name": "unresolved", "reason": type(exc).__name__}
    threads = {
        "num_threads": os.environ.get("QLIB_MODEL_NUM_THREADS", "1"),
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS", "1"),
        "mkl_num_threads": os.environ.get("MKL_NUM_THREADS", "1"),
        "openblas_num_threads": os.environ.get("OPENBLAS_NUM_THREADS", "1"),
        "numexpr_num_threads": os.environ.get("NUMEXPR_NUM_THREADS", "1"),
    }
    if any(str(value).strip().lower() == "auto" for value in threads.values()):
        raise ValueError("model protocol thread counts cannot be auto")
    payload: dict[str, Any] = {
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "numpy_version": _version("numpy"),
        "pandas_version": _version("pandas"),
        "scipy_version": _version("scipy"),
        "scikit_learn_version": _version("scikit-learn"),
        "lightgbm_version": _version("lightgbm"),
        "qlib_commit_sha": qlib_commit_sha,
        **threads,
        "blas_backend": blas_backend,
    }
    payload["environment_lock_sha256"] = canonical_hash(payload)
    return payload


def validate_pre_test_freeze(payload: dict[str, object]) -> None:
    missing = freeze_schema_missing(payload)
    if missing:
        raise ValueError(f"pre-test freeze missing fields: {missing}")
    if payload["experiment_class"] != "post_observation_research":
        raise ValueError("pre-test freeze experiment_class is not research-scoped")
    if payload["authoritative_execution"] is not False:
        raise ValueError("authoritative_execution must remain false")
    if payload["unbiased_final_estimate"] is not False:
        raise ValueError("unbiased_final_estimate must remain false")
    if set(PRE_TEST_FREEZE_REQUIRED_FIELDS) - set(payload):
        raise AssertionError("unreachable incomplete freeze")


def load_freeze_before_test(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise PermissionError("test release blocked: missing pre-test freeze manifest")
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_pre_test_freeze(payload)
    return payload
