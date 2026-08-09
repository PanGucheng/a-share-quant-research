from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from qlib_baseline.settings import ProjectSettings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_SCRIPTS = (
    "daily_update.py",
    "run_forward_prediction_v1.py",
    "update_forward_labels_v1.py",
    "run_paper_portfolio_v1.py",
    "show_forward_status_v1.py",
)
CONSOLE_SCRIPTS = {
    "qlib-daily-update": "qlib_baseline.cli.daily_update:main",
    "qlib-forward-predict": "qlib_baseline.cli.forward_predict:main",
    "qlib-forward-label-update": "qlib_baseline.cli.forward_label_update:main",
    "qlib-paper-portfolio": "qlib_baseline.cli.paper_portfolio:main",
    "qlib-forward-status": "qlib_baseline.cli.forward_status:main",
}


def _settings(tmp_path: Path) -> ProjectSettings:
    return ProjectSettings(
        project_root=tmp_path,
        qlib_source=tmp_path / "qlib-source",
        qlib_provider=tmp_path / "provider",
        daily_update_cache=tmp_path / "cache",
        outputs_dir=tmp_path / "outputs",
        artifacts_dir=tmp_path / "artifacts",
        reports_dir=tmp_path / "reports",
        tmp_dir=tmp_path / "tmp",
    )


def test_legacy_scripts_are_exact_packaged_cli_wrappers() -> None:
    from qlib_baseline.cli import (
        daily_update,
        forward_label_update,
        forward_predict,
        forward_status,
        paper_portfolio,
    )
    from scripts import (
        daily_update as legacy_daily_update,
        run_forward_prediction_v1 as legacy_forward_predict,
        run_paper_portfolio_v1 as legacy_paper_portfolio,
        show_forward_status_v1 as legacy_forward_status,
        update_forward_labels_v1 as legacy_forward_label_update,
    )

    assert legacy_daily_update.main is daily_update.main
    assert legacy_forward_predict.main is forward_predict.main
    assert legacy_forward_label_update.main is forward_label_update.main
    assert legacy_paper_portfolio.main is paper_portfolio.main
    assert legacy_forward_status.main is forward_status.main


def test_legacy_scripts_execute_without_path_bootstrap() -> None:
    for name in ACTIVE_SCRIPTS:
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / name), "--help"],
            cwd=PROJECT_ROOT.parent,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "usage:" in result.stdout


def test_active_entrypoints_have_no_path_bootstrap_or_machine_path() -> None:
    paths = [PROJECT_ROOT / "scripts" / name for name in ACTIVE_SCRIPTS]
    paths.extend(
        [
            PROJECT_ROOT / "daily_update/pipeline.py",
            *sorted((PROJECT_ROOT / "qlib_baseline/cli").glob("*.py")),
        ]
    )
    for path in paths:
        source = path.read_text(encoding="utf-8")
        assert "sys.path.insert" not in source, path
        assert "E:/qlib_prj" not in source, path


def test_pyproject_registers_all_active_console_scripts() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for name, target in CONSOLE_SCRIPTS.items():
        assert f'{name} = "{target}"' in pyproject


def test_daily_update_defaults_come_from_project_settings(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    from qlib_baseline.cli import daily_update

    settings = _settings(tmp_path)
    captured = {}
    monkeypatch.setattr(daily_update, "load_settings", lambda *_args, **_kwargs: settings)

    def fake_run(config):
        captured["config"] = config
        return {"status": "ready"}

    monkeypatch.setattr(daily_update, "run", fake_run)

    assert daily_update.main(["--target-date", "2026-08-07"]) == 0

    config = captured["config"]
    assert config.target_date == date(2026, 8, 7)
    assert config.cache_dir == settings.daily_update_cache
    assert config.output_dir == settings.outputs_dir / "daily_data_update_v1"
    assert config.universe_file == (
        settings.qlib_provider / "instruments/all_stock_shsz_liquid2000.txt"
    )
    assert config.qlib_source == settings.qlib_source
    assert json.loads(capsys.readouterr().out)["status"] == "ready"


def test_forward_cli_defaults_come_from_project_settings(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    from qlib_baseline.cli import forward_predict

    settings = _settings(tmp_path)
    captured = {}
    monkeypatch.setattr(forward_predict, "load_settings", lambda *_args, **_kwargs: settings)
    monkeypatch.setattr(
        forward_predict,
        "finalize_prediction_commit",
        lambda **kwargs: captured.update(kwargs) or {"status": "committed"},
    )

    result = forward_predict.main(
        [
            "--date",
            "2026-08-07",
            "--calendar-file",
            "calendar.txt",
            "--finalize-commit",
            "a" * 40,
        ]
    )

    assert result == 0
    assert captured["repository_root"] == settings.project_root
    assert captured["output_root"] == settings.outputs_dir / "forward"
    assert captured["freeze_path"] == (
        settings.outputs_dir
        / "prospective_forward_hardening_v1/current/forward_candidate_freeze.json"
    )
    assert json.loads(capsys.readouterr().out)["status"] == "committed"


def test_label_update_defaults_come_from_project_settings(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    from qlib_baseline.cli import forward_label_update

    settings = _settings(tmp_path)
    captured = {}
    monkeypatch.setattr(
        forward_label_update,
        "load_settings",
        lambda *_args, **_kwargs: settings,
    )
    monkeypatch.setattr(
        forward_label_update,
        "update_mature_forward_labels",
        lambda **kwargs: captured.update(kwargs) or {"status": "updated"},
    )

    result = forward_label_update.main(
        [
            "--as-of-date",
            "2026-08-12",
            "--calendar-file",
            "calendar.txt",
            "--label-dir",
            "labels",
        ]
    )

    assert result == 0
    assert captured["repository_root"] == settings.project_root
    assert captured["output_root"] == settings.outputs_dir / "forward"
    assert captured["state_path"] == settings.outputs_dir / "forward/status.json"
    assert json.loads(capsys.readouterr().out)["status"] == "updated"


def test_paper_and_status_defaults_come_from_project_settings(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    from qlib_baseline.cli import forward_status, paper_portfolio

    settings = _settings(tmp_path)
    config_path = settings.project_root / "configs/strategy_v1_paper_portfolio_v1.yaml"
    loaded = {}
    monkeypatch.setattr(paper_portfolio, "load_settings", lambda *_args, **_kwargs: settings)

    def fake_load_paper_config(path):
        loaded["path"] = path
        return {"stage_id": "test"}

    monkeypatch.setattr(paper_portfolio, "load_paper_config", fake_load_paper_config)
    monkeypatch.setattr(
        paper_portfolio,
        "refresh_paper_execution",
        lambda _config: {"status": "waiting"},
    )
    assert paper_portfolio.main(["--refresh-only"]) == 0
    assert loaded["path"] == config_path
    assert json.loads(capsys.readouterr().out)["execution"]["status"] == "waiting"

    status_path = settings.outputs_dir / "forward/status.json"
    status_path.parent.mkdir(parents=True)
    status_path.write_text('{"status": "pending_label"}', encoding="utf-8")
    monkeypatch.setattr(forward_status, "load_settings", lambda *_args, **_kwargs: settings)
    assert forward_status.main([]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "pending_label"
