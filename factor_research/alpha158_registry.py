from __future__ import annotations

from pathlib import Path

from factor_research.catalog import FactorCatalogEntry, load_factor_catalog
from factor_research.registry import FactorSpec


def catalog_entry_to_spec(entry: FactorCatalogEntry) -> FactorSpec:
    return FactorSpec(
        name=entry.registry_name,
        category=entry.category,
        expected_direction=entry.expected_direction,
        dependencies=entry.required_fields,
        description=entry.notes or f"{entry.source_project} factor {entry.name}",
        labels=entry.labels,
        enabled=entry.enabled,
    )


def load_external_factor_specs(
    catalog_path: Path,
    requested_factors: list[str],
    labels: list[str],
    *,
    require_runnable: bool = True,
    require_enabled: bool = True,
) -> list[FactorSpec]:
    entries = load_factor_catalog(catalog_path)
    requested = set(requested_factors)
    label_set = set(labels)
    selected: list[FactorCatalogEntry] = []
    for entry in entries:
        if entry.name not in requested and entry.registry_name not in requested:
            continue
        if require_enabled and not entry.enabled:
            raise ValueError(f"External factor is not enabled: {entry.name}")
        if require_runnable and not entry.runnable:
            raise ValueError(f"External factor is not runnable: {entry.name}")
        if not (label_set & set(entry.labels)):
            continue
        selected.append(entry)
    missing = sorted(requested - {entry.name for entry in selected} - {entry.registry_name for entry in selected})
    if missing:
        raise ValueError(f"Requested external factors not found in catalog: {missing}")
    return [catalog_entry_to_spec(entry) for entry in selected]
