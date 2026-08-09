from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

from qlib_baseline.settings import (
    ProjectSettings,
    SettingsError,
    load_settings,
    selected_config_files,
)


EXPECTED_PYTHON = (3, 10)
DEPENDENCIES = (
    ("PyYAML", "yaml"),
    ("pyqlib", "qlib"),
    ("lightgbm", "lightgbm"),
    ("pandas", "pandas"),
    ("numpy", "numpy"),
    ("pandera", "pandera"),
    ("baostock", "baostock"),
)


def _check(name: str, status: str, detail: str) -> dict[str, str]:
    return {"name": name, "status": status, "detail": detail}


def _dependency_check(distribution: str, module: str) -> dict[str, str]:
    if importlib.util.find_spec(module) is None:
        return _check(f"dependency:{distribution}", "fail", f"module {module!r} is not importable")
    try:
        version = metadata.version(distribution)
    except metadata.PackageNotFoundError:
        version = "unknown/editable"
    return _check(f"dependency:{distribution}", "pass", version)


def _external_path_check(name: str, path: Path | None, markers: tuple[str, ...]) -> dict[str, str]:
    if path is None:
        return _check(f"path:{name}", "fail", "not configured; add configs/project.local.yaml")
    missing = [marker for marker in markers if not (path / marker).exists()]
    if not path.exists():
        return _check(f"path:{name}", "fail", f"does not exist: {path}")
    if missing:
        return _check(
            f"path:{name}",
            "fail",
            f"missing expected entries {missing}: {path}",
        )
    return _check(f"path:{name}", "pass", str(path))


def _qlib_import_origin() -> Path | None:
    spec = importlib.util.find_spec("qlib")
    if spec is None or not spec.origin or spec.origin in {"built-in", "frozen"}:
        return None
    return Path(spec.origin).resolve()


def _qlib_source_alignment_check(qlib_source: Path | None) -> dict[str, str]:
    origin = _qlib_import_origin()
    if qlib_source is None:
        return _check(
            "runtime:qlib_source_alignment",
            "warn",
            f"imported={origin or 'unavailable'}; configured source is not set",
        )
    configured = qlib_source.resolve()
    package_root = (configured / "qlib").resolve()
    if origin is None:
        return _check(
            "runtime:qlib_source_alignment",
            "fail",
            f"imported=unavailable; configured={configured}",
        )
    try:
        origin.relative_to(package_root)
        aligned = True
    except ValueError:
        aligned = False
    return _check(
        "runtime:qlib_source_alignment",
        "pass" if aligned else "fail",
        f"imported={origin}; configured={configured}",
    )


def build_report(settings: ProjectSettings, *, config_files: tuple[Path, ...] = ()) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    version = sys.version_info[:2]
    checks.append(
        _check(
            "runtime:python",
            "pass" if version == EXPECTED_PYTHON else "fail",
            f"{sys.executable} ({sys.version.split()[0]}); expected 3.10.x",
        )
    )
    checks.extend(_dependency_check(distribution, module) for distribution, module in DEPENDENCIES)
    checks.append(
        _external_path_check(
            "qlib_source",
            settings.qlib_source,
            ("qlib/__init__.py", "scripts/dump_bin.py"),
        )
    )
    checks.append(_qlib_source_alignment_check(settings.qlib_source))
    checks.append(
        _external_path_check(
            "qlib_provider",
            settings.qlib_provider,
            ("calendars/day.txt", "instruments"),
        )
    )
    if settings.daily_update_cache is None:
        checks.append(
            _check(
                "path:daily_update_cache",
                "fail",
                "not configured; add configs/project.local.yaml",
            )
        )
    else:
        cache_parent = settings.daily_update_cache.parent
        cache_ready = settings.daily_update_cache.exists() or cache_parent.is_dir()
        checks.append(
            _check(
                "path:daily_update_cache",
                "pass" if cache_ready else "fail",
                str(settings.daily_update_cache),
            )
        )

    for name in ("outputs_dir", "artifacts_dir", "tmp_dir"):
        path = getattr(settings, name)
        checks.append(
            _check(
                f"path:{name}",
                "pass" if path.is_dir() else "warn",
                str(path),
            )
        )
    checks.append(
        _check(
            "path:reports_dir",
            "pass" if settings.reports_dir.is_dir() else "warn",
            f"{settings.reports_dir} (planned for Phase 4 if absent)",
        )
    )
    failed = [item for item in checks if item["status"] == "fail"]
    return {
        "status": "ready" if not failed else "incomplete",
        "project_root": str(settings.project_root),
        "config_files": [str(path) for path in config_files],
        "settings": settings.as_dict(),
        "checks": checks,
        "failure_count": len(failed),
    }


def _print_human(report: dict[str, Any]) -> None:
    print(f"qlib-baseline doctor: {report['status']}")
    print(f"project_root: {report['project_root']}")
    for path in report["config_files"]:
        print(f"config: {path}")
    for item in report["checks"]:
        print(f"[{item['status'].upper():4}] {item['name']}: {item['detail']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect qlib-baseline settings and runtime")
    parser.add_argument("--project-config", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return nonzero when the configured Forward/Daily runtime is incomplete.",
    )
    args = parser.parse_args(argv)
    try:
        settings = load_settings(args.project_config)
        config_files = selected_config_files(args.project_config)
        report = build_report(settings, config_files=config_files)
    except SettingsError as exc:
        report = {"status": "invalid_settings", "error": str(exc), "failure_count": 1}
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"qlib-baseline doctor: invalid_settings\n[FAIL] settings: {exc}")
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_human(report)
    return 1 if args.strict and report["failure_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
