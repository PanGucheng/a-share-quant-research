from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import yaml


CATALOG_VERSION = 1


@dataclass(frozen=True)
class FactorCatalogEntry:
    name: str
    category: str
    source_project: str
    source_file: str
    source_function: str
    source_commit: str
    license: str
    expected_direction: str
    required_fields: tuple[str, ...]
    labels: tuple[str, ...]
    stage: str
    enabled: bool
    runnable: bool
    compute_adapter: str
    registry_name: str
    notes: str = ""


REQUIRED_FIELDS = [
    "name",
    "category",
    "source_project",
    "source_file",
    "source_function",
    "source_commit",
    "license",
    "expected_direction",
    "required_fields",
    "labels",
    "stage",
    "enabled",
    "runnable",
    "compute_adapter",
]


def _as_tuple(value: object, field_name: str, factor_name: str) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    raise ValueError(f"{factor_name}.{field_name} must be a string or list")


def _entry_from_mapping(data: dict) -> FactorCatalogEntry:
    missing = [field for field in REQUIRED_FIELDS if field not in data]
    name = str(data.get("name", "<unknown>"))
    if missing:
        raise ValueError(f"factor catalog entry {name} missing required fields: {missing}")
    registry_name = str(data.get("registry_name") or data["name"])
    return FactorCatalogEntry(
        name=str(data["name"]),
        category=str(data["category"]),
        source_project=str(data["source_project"]),
        source_file=str(data["source_file"]),
        source_function=str(data["source_function"]),
        source_commit=str(data["source_commit"]),
        license=str(data["license"]),
        expected_direction=str(data["expected_direction"]),
        required_fields=_as_tuple(data["required_fields"], "required_fields", name),
        labels=_as_tuple(data["labels"], "labels", name),
        stage=str(data["stage"]),
        enabled=bool(data["enabled"]),
        runnable=bool(data["runnable"]),
        compute_adapter=str(data["compute_adapter"]),
        registry_name=registry_name,
        notes=str(data.get("notes", "")),
    )


def load_factor_catalog(path: Path) -> list[FactorCatalogEntry]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    version = int(payload.get("version", 0))
    if version != CATALOG_VERSION:
        raise ValueError(f"Unsupported factor catalog version: {version}")
    raw_factors = payload.get("factors", [])
    if not isinstance(raw_factors, list):
        raise ValueError("factor catalog must contain a list under 'factors'")
    entries = [_entry_from_mapping(item) for item in raw_factors]
    names = [entry.name for entry in entries]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"Duplicate factor catalog entries: {duplicates}")
    return entries


def select_entries(
    entries: Iterable[FactorCatalogEntry],
    *,
    enabled_only: bool = True,
    runnable_only: bool = True,
    stages: Iterable[str] | None = None,
    categories: Iterable[str] | None = None,
    sources: Iterable[str] | None = None,
    names: Iterable[str] | None = None,
    max_factors: int | None = None,
) -> list[FactorCatalogEntry]:
    stage_set = {str(item) for item in stages or []}
    category_set = {str(item) for item in categories or []}
    source_set = {str(item) for item in sources or []}
    name_set = {str(item) for item in names or []}
    selected: list[FactorCatalogEntry] = []
    for entry in entries:
        if enabled_only and not entry.enabled:
            continue
        if runnable_only and not entry.runnable:
            continue
        if stage_set and entry.stage not in stage_set:
            continue
        if category_set and entry.category not in category_set:
            continue
        if source_set and entry.source_project not in source_set:
            continue
        if name_set and entry.name not in name_set and entry.registry_name not in name_set:
            continue
        selected.append(entry)
    if max_factors is not None:
        selected = selected[: int(max_factors)]
    return selected


def catalog_frame(entries: Iterable[FactorCatalogEntry]) -> pd.DataFrame:
    rows = []
    for entry in entries:
        row = asdict(entry)
        row["required_fields"] = ",".join(entry.required_fields)
        row["labels"] = ",".join(entry.labels)
        rows.append(row)
    columns = [
        "name",
        "registry_name",
        "category",
        "stage",
        "enabled",
        "runnable",
        "expected_direction",
        "source_project",
        "source_file",
        "source_function",
        "source_commit",
        "license",
        "compute_adapter",
        "required_fields",
        "labels",
        "notes",
    ]
    return pd.DataFrame(rows, columns=columns)


def validate_against_registry(entries: Iterable[FactorCatalogEntry], registry_names: Iterable[str]) -> pd.DataFrame:
    registry_set = set(registry_names)
    rows = []
    for entry in entries:
        rows.append(
            {
                "name": entry.name,
                "registry_name": entry.registry_name,
                "enabled": entry.enabled,
                "runnable": entry.runnable,
                "registered": entry.registry_name in registry_set,
                "status": "ok"
                if (not entry.runnable or entry.registry_name in registry_set)
                else "runnable_missing_registry",
                "source_project": entry.source_project,
                "stage": entry.stage,
            }
        )
    return pd.DataFrame(rows)
