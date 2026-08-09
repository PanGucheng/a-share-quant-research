from __future__ import annotations

import json
from pathlib import Path

from qlib_baseline.cli import doctor
from qlib_baseline.settings import ProjectSettings


def _settings(tmp_path: Path) -> ProjectSettings:
    source = tmp_path / "qlib-source"
    (source / "qlib").mkdir(parents=True)
    (source / "qlib/__init__.py").write_text("", encoding="utf-8")
    (source / "scripts").mkdir()
    (source / "scripts/dump_bin.py").write_text("", encoding="utf-8")
    provider = tmp_path / "provider"
    (provider / "calendars").mkdir(parents=True)
    (provider / "calendars/day.txt").write_text("2026-08-07\n", encoding="utf-8")
    (provider / "instruments").mkdir()
    cache = tmp_path / "cache"
    cache.mkdir()
    for name in ("outputs", "artifacts", "tmp"):
        (tmp_path / name).mkdir()
    return ProjectSettings(
        project_root=tmp_path,
        qlib_source=source,
        qlib_provider=provider,
        daily_update_cache=cache,
        outputs_dir=tmp_path / "outputs",
        artifacts_dir=tmp_path / "artifacts",
        reports_dir=tmp_path / "reports",
        tmp_dir=tmp_path / "tmp",
    )


def test_doctor_reports_current_interpreter_and_paths(tmp_path: Path) -> None:
    report = doctor.build_report(_settings(tmp_path), config_files=(tmp_path / "config.yaml",))
    checks = {item["name"]: item for item in report["checks"]}
    assert checks["runtime:python"]["detail"].startswith(str(doctor.sys.executable))
    assert checks["path:qlib_source"]["status"] == "pass"
    assert checks["path:qlib_provider"]["status"] == "pass"
    assert checks["path:reports_dir"]["status"] == "warn"


def test_doctor_default_is_diagnostic_and_strict_is_enforcing(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    settings = _settings(tmp_path)
    report = {
        "status": "incomplete",
        "project_root": str(tmp_path),
        "config_files": [],
        "settings": settings.as_dict(),
        "checks": [],
        "failure_count": 1,
    }
    monkeypatch.setattr(doctor, "load_settings", lambda *_args, **_kwargs: settings)
    monkeypatch.setattr(doctor, "selected_config_files", lambda *_args, **_kwargs: ())
    monkeypatch.setattr(doctor, "build_report", lambda *_args, **_kwargs: report)
    assert doctor.main(["--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "incomplete"
    assert doctor.main(["--json", "--strict"]) == 1
