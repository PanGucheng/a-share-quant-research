from __future__ import annotations

import hashlib
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path


RUNTIME_PATHS = ("qlib", "pyproject.toml", "setup.py", "setup.cfg")


def _git(source: Path, *args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=source,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.returncode, result.stdout.strip()


def _path_fingerprint(path: Path) -> str:
    return hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()


def audit_qlib_environment(source: Path, provider: Path, expected_commit: str) -> dict[str, object]:
    source = source.resolve()
    provider = provider.resolve()
    _, commit = _git(source, "rev-parse", "HEAD")
    _, status = _git(source, "status", "--short")
    _, runtime_status = _git(source, "status", "--short", "--", *RUNTIME_PATHS)
    try:
        package_version = importlib.metadata.version("pyqlib")
    except importlib.metadata.PackageNotFoundError:
        package_version = "missing"
    return {
        "python_version": ".".join(map(str, sys.version_info[:3])),
        "python_3_10": sys.version_info[:2] == (3, 10),
        "pyqlib_version": package_version,
        "qlib_source_commit": commit,
        "expected_qlib_commit": expected_commit,
        "qlib_commit_matches": commit == expected_commit,
        "qlib_source_exists": source.is_dir(),
        "qlib_provider_exists": provider.is_dir(),
        "provider_calendar_exists": (provider / "calendars" / "day.txt").is_file(),
        "provider_instruments_exists": (provider / "instruments").is_dir(),
        "provider_features_exists": (provider / "features").is_dir(),
        "source_worktree_dirty": bool(status),
        "source_dirty_files": status.splitlines() if status else [],
        "runtime_code_dirty": bool(runtime_status),
        "runtime_dirty_files": runtime_status.splitlines() if runtime_status else [],
        "source_path_fingerprint": _path_fingerprint(source),
        "provider_path_fingerprint": _path_fingerprint(provider),
    }


def environment_ready(payload: dict[str, object]) -> bool:
    required = [
        "python_3_10",
        "qlib_commit_matches",
        "qlib_source_exists",
        "qlib_provider_exists",
        "provider_calendar_exists",
        "provider_instruments_exists",
        "provider_features_exists",
    ]
    return all(bool(payload[key]) for key in required) and not bool(payload["runtime_code_dirty"])


def write_environment_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
