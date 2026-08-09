from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_SCHEMA_VERSION = 1
BASE_CONFIG_RELATIVE = Path("configs/project.yaml")
LOCAL_CONFIG_RELATIVE = Path("configs/project.local.yaml")

_CONFIG_TO_FIELD = {
    "qlib_source": "qlib_source",
    "qlib_provider": "qlib_provider",
    "daily_update_cache": "daily_update_cache",
    "outputs": "outputs_dir",
    "artifacts": "artifacts_dir",
    "reports": "reports_dir",
    "tmp": "tmp_dir",
}
_FIELD_TO_ENV = {
    "qlib_source": "QLIB_BASELINE_QLIB_SOURCE",
    "qlib_provider": "QLIB_BASELINE_QLIB_PROVIDER",
    "daily_update_cache": "QLIB_BASELINE_DAILY_UPDATE_CACHE",
    "outputs_dir": "QLIB_BASELINE_OUTPUTS_DIR",
    "artifacts_dir": "QLIB_BASELINE_ARTIFACTS_DIR",
    "reports_dir": "QLIB_BASELINE_REPORTS_DIR",
    "tmp_dir": "QLIB_BASELINE_TMP_DIR",
}
_REQUIRED_REPOSITORY_FIELDS = ("outputs_dir", "artifacts_dir", "reports_dir", "tmp_dir")


class SettingsError(ValueError):
    """Raised when project settings cannot be loaded safely."""


@dataclass(frozen=True)
class ProjectSettings:
    project_root: Path
    qlib_source: Path | None
    qlib_provider: Path | None
    daily_update_cache: Path | None
    outputs_dir: Path
    artifacts_dir: Path
    reports_dir: Path
    tmp_dir: Path

    def as_dict(self) -> dict[str, str | None]:
        return {
            field: str(getattr(self, field)) if getattr(self, field) is not None else None
            for field in self.__dataclass_fields__
        }


def _resolve_from_root(value: str | Path | None, project_root: Path) -> Path | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    expanded = Path(os.path.expandvars(os.path.expanduser(raw)))
    return expanded.resolve() if expanded.is_absolute() else (project_root / expanded).resolve()


def _read_config(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise SettingsError(f"Project settings file does not exist: {path}")
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise SettingsError(f"Project settings YAML is invalid: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SettingsError(f"Project settings must be a mapping: {path}")
    if payload.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise SettingsError(
            f"Project settings schema_version must be {CONFIG_SCHEMA_VERSION}: {path}"
        )
    paths = payload.get("paths")
    if not isinstance(paths, dict):
        raise SettingsError(f"Project settings paths must be a mapping: {path}")
    unknown = sorted(set(paths) - set(_CONFIG_TO_FIELD))
    if unknown:
        raise SettingsError(f"Unknown project path settings in {path}: {unknown}")
    return payload


def _override_config_path(
    *,
    project_root: Path,
    config_path: str | Path | None,
    environ: Mapping[str, str],
) -> Path | None:
    explicit = config_path or environ.get("QLIB_BASELINE_CONFIG")
    if explicit:
        return _resolve_from_root(explicit, project_root)
    local = project_root / LOCAL_CONFIG_RELATIVE
    return local.resolve() if local.is_file() else None


def selected_config_files(
    config_path: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    project_root: str | Path | None = None,
) -> tuple[Path, ...]:
    """Return the committed base config and optional selected override config."""

    root = Path(project_root or PROJECT_ROOT).resolve()
    environment = os.environ if environ is None else environ
    base = (root / BASE_CONFIG_RELATIVE).resolve()
    override = _override_config_path(
        project_root=root,
        config_path=config_path,
        environ=environment,
    )
    if override is None or override == base:
        return (base,)
    return base, override


def load_settings(
    config_path: str | Path | None = None,
    *,
    cli_overrides: Mapping[str, str | Path | None] | None = None,
    environ: Mapping[str, str] | None = None,
    project_root: str | Path | None = None,
) -> ProjectSettings:
    """Load portable base settings plus one optional machine-local override.

    Field precedence is CLI override, environment variable, selected YAML override,
    then committed base YAML. Relative paths are always resolved from the repository
    root, never from the caller's current working directory.
    """

    root = Path(project_root or PROJECT_ROOT).resolve()
    environment = os.environ if environ is None else environ
    merged: dict[str, object] = {}
    for path in selected_config_files(
        config_path,
        environ=environment,
        project_root=root,
    ):
        payload = _read_config(path)
        merged.update(payload["paths"])

    values: dict[str, Path | None] = {
        field: _resolve_from_root(merged.get(config_key), root)
        for config_key, field in _CONFIG_TO_FIELD.items()
    }
    for field, env_name in _FIELD_TO_ENV.items():
        if environment.get(env_name):
            values[field] = _resolve_from_root(environment[env_name], root)

    overrides = dict(cli_overrides or {})
    unknown_overrides = sorted(set(overrides) - set(_FIELD_TO_ENV))
    if unknown_overrides:
        raise SettingsError(f"Unknown CLI project path overrides: {unknown_overrides}")
    for field, value in overrides.items():
        if value is not None:
            values[field] = _resolve_from_root(value, root)

    missing = [field for field in _REQUIRED_REPOSITORY_FIELDS if values.get(field) is None]
    if missing:
        raise SettingsError(f"Required repository paths are not configured: {missing}")

    return ProjectSettings(project_root=root, **values)  # type: ignore[arg-type]
