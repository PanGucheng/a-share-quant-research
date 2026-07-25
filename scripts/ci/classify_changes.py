from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path
from typing import Iterable


ZERO_SHA = "0" * 40
ROOT_DOC_NAMES = {"readme.md", "readme.zh-cn.md", "contributing.md", "changelog.md"}
QLIB_EXACT_PATHS = {
    ".github/workflows/research-validation-ci.yml",
    "tests/test_qlib_exchange_runtime.py",
    "tests/test_qlib_integration_contracts.py",
}
DEPENDENCY_NAMES = {
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "poetry.lock",
    "pdm.lock",
    "uv.lock",
}


def normalize_path(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def is_docs_fast_path(path: str) -> bool:
    normalized = normalize_path(path)
    lowered = normalized.lower()
    if lowered.startswith("docs/"):
        return True
    return "/" not in normalized and lowered in ROOT_DOC_NAMES


def is_dependency_path(path: str) -> bool:
    normalized = normalize_path(path)
    name = Path(normalized).name.lower()
    return (
        name in DEPENDENCY_NAMES
        or name.startswith("requirements")
        and name.endswith((".txt", ".in"))
        or normalized.lower().startswith(("environment", "conda"))
        and name.endswith((".yml", ".yaml"))
    )


def is_qlib_runtime_path(path: str) -> bool:
    normalized = normalize_path(path)
    lowered = normalized.lower()
    name = Path(lowered).name
    if lowered in QLIB_EXACT_PATHS:
        return True
    if lowered.startswith(("qlib_integration/", "scripts/ci/")):
        return True
    if is_dependency_path(lowered):
        return True
    if lowered.startswith(".github/workflows/"):
        return True
    if lowered.startswith("research_validation/qlib"):
        return True
    if lowered.startswith("configs/") and re.search(
        r"(qlib_exchange|execution_reconciliation|a_share_execution)", name
    ):
        return True
    if lowered.startswith("scripts/") and re.search(
        r"(qlib_exchange|execution_reconciliation|reconcile_execution|"
        r"corrected_oos_execution|a_share_execution)",
        name,
    ):
        return True
    return False


def classify_paths(paths: Iterable[str]) -> dict[str, object]:
    normalized = sorted({normalize_path(item) for item in paths if item.strip()})
    docs_changed = any(is_docs_fast_path(item) for item in normalized)
    docs_only = bool(normalized) and all(is_docs_fast_path(item) for item in normalized)
    research_code_changed = any(not is_docs_fast_path(item) for item in normalized)
    qlib_changed = any(is_qlib_runtime_path(item) for item in normalized)
    return {
        "docs_changed": docs_changed,
        "research_code_changed": research_code_changed,
        "qlib_changed": qlib_changed,
        "docs_only": docs_only,
        "changed_count": len(normalized),
        "paths": normalized,
    }


def resolve_diff_base(base: str, head: str) -> tuple[str, str]:
    resolved_head = head.strip() or "HEAD"
    resolved_base = base.strip()
    if not resolved_base or resolved_base == ZERO_SHA:
        resolved_base = f"{resolved_head}^"
    return resolved_base, resolved_head


def changed_paths(base: str, head: str) -> list[str]:
    resolved_base, resolved_head = resolve_diff_base(base, head)
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACDMRTUXB", resolved_base, resolved_head],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def write_github_output(path: Path, result: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for key in ("docs_changed", "research_code_changed", "qlib_changed", "docs_only"):
            handle.write(f"{key}={str(bool(result[key])).lower()}\n")
        handle.write(f"changed_count={result['changed_count']}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify repository changes for tiered CI.")
    parser.add_argument("--base", default=os.environ.get("BASE_SHA", ""))
    parser.add_argument("--head", default=os.environ.get("HEAD_SHA", "HEAD"))
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    result = classify_paths(changed_paths(args.base, args.head))
    for key in (
        "docs_changed",
        "research_code_changed",
        "qlib_changed",
        "docs_only",
        "changed_count",
    ):
        print(f"{key}={result[key]}")
    print("changed_paths:")
    for path in result["paths"]:
        print(f"  {path}")
    if args.github_output:
        write_github_output(args.github_output, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
