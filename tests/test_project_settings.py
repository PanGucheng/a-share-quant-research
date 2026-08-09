from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from qlib_baseline.settings import SettingsError, load_settings, selected_config_files


def _write_config(root: Path, relative: str, paths: dict[str, object]) -> Path:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        yaml.safe_dump({"schema_version": 1, "paths": paths}, sort_keys=False),
        encoding="utf-8",
    )
    return target


def _portable_paths() -> dict[str, object]:
    return {
        "qlib_source": None,
        "qlib_provider": None,
        "daily_update_cache": None,
        "outputs": "outputs",
        "artifacts": "artifacts",
        "reports": "reports",
        "tmp": "tmp",
    }


def test_portable_base_config_keeps_machine_paths_unset(tmp_path: Path) -> None:
    _write_config(tmp_path, "configs/project.yaml", _portable_paths())
    settings = load_settings(project_root=tmp_path, environ={})
    assert settings.project_root == tmp_path.resolve()
    assert settings.qlib_source is None
    assert settings.qlib_provider is None
    assert settings.daily_update_cache is None
    assert settings.outputs_dir == (tmp_path / "outputs").resolve()
    assert settings.reports_dir == (tmp_path / "reports").resolve()


def test_partial_local_config_merges_with_committed_base(tmp_path: Path) -> None:
    _write_config(tmp_path, "configs/project.yaml", _portable_paths())
    _write_config(
        tmp_path,
        "configs/project.local.yaml",
        {
            "qlib_source": "../qlib-source",
            "qlib_provider": "../qlib-data/provider",
            "daily_update_cache": "../qlib-data/cache",
        },
    )
    settings = load_settings(project_root=tmp_path, environ={})
    assert settings.qlib_source == (tmp_path / "../qlib-source").resolve()
    assert settings.qlib_provider == (tmp_path / "../qlib-data/provider").resolve()
    assert settings.outputs_dir == (tmp_path / "outputs").resolve()
    assert selected_config_files(project_root=tmp_path, environ={}) == (
        (tmp_path / "configs/project.yaml").resolve(),
        (tmp_path / "configs/project.local.yaml").resolve(),
    )


def test_config_and_field_precedence_is_explicit(tmp_path: Path) -> None:
    _write_config(tmp_path, "configs/project.yaml", _portable_paths())
    env_config = _write_config(
        tmp_path,
        "env.yaml",
        {"qlib_source": "env-config-source"},
    )
    explicit_config = _write_config(
        tmp_path,
        "explicit.yaml",
        {"qlib_source": "explicit-config-source"},
    )
    environment = {
        "QLIB_BASELINE_CONFIG": str(env_config),
        "QLIB_BASELINE_QLIB_SOURCE": "environment-source",
        "QLIB_BASELINE_OUTPUTS_DIR": "environment-outputs",
    }
    settings = load_settings(
        explicit_config,
        cli_overrides={"qlib_source": "cli-source", "outputs_dir": "cli-outputs"},
        project_root=tmp_path,
        environ=environment,
    )
    assert selected_config_files(
        explicit_config,
        project_root=tmp_path,
        environ=environment,
    )[-1] == explicit_config.resolve()
    assert settings.qlib_source == (tmp_path / "cli-source").resolve()
    assert settings.outputs_dir == (tmp_path / "cli-outputs").resolve()


def test_paths_resolve_from_project_root_not_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_config(tmp_path, "configs/project.yaml", _portable_paths())
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    settings = load_settings(project_root=tmp_path, environ={})
    assert settings.tmp_dir == (tmp_path / "tmp").resolve()


def test_invalid_schema_and_unknown_keys_fail_loudly(tmp_path: Path) -> None:
    _write_config(tmp_path, "configs/project.yaml", {**_portable_paths(), "unknown": "x"})
    with pytest.raises(SettingsError, match="Unknown project path settings"):
        load_settings(project_root=tmp_path, environ={})

    (tmp_path / "configs/project.yaml").write_text(
        "schema_version: 2\npaths: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(SettingsError, match="schema_version must be 1"):
        load_settings(project_root=tmp_path, environ={})


def test_unknown_cli_override_fails_loudly(tmp_path: Path) -> None:
    _write_config(tmp_path, "configs/project.yaml", _portable_paths())
    with pytest.raises(SettingsError, match="Unknown CLI project path overrides"):
        load_settings(
            project_root=tmp_path,
            environ={},
            cli_overrides={"python_executable": "python.exe"},
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows path semantics")
def test_windows_absolute_paths_remain_absolute(tmp_path: Path) -> None:
    _write_config(tmp_path, "configs/project.yaml", _portable_paths())
    windows_source = "E:/qlib_prj/qlib_clone"
    _write_config(
        tmp_path,
        "configs/project.local.yaml",
        {"qlib_source": windows_source},
    )

    settings = load_settings(project_root=tmp_path, environ={})

    assert settings.qlib_source == Path(windows_source).resolve()
