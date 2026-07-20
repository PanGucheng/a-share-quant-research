from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from factor_research.catalog import FactorCatalogEntry


def evenly_spaced(items: list[FactorCatalogEntry], count: int) -> list[FactorCatalogEntry]:
    values = sorted(items, key=lambda entry: entry.name)
    if count < 0 or count > len(values):
        raise ValueError(f"cannot select {count} entries from {len(values)} candidates")
    if count == 0:
        return []
    indices = [min(len(values) - 1, int((index + 0.5) * len(values) / count)) for index in range(count)]
    if len(set(indices)) != count:
        raise ValueError("even sampling produced duplicate indices")
    return [values[index] for index in indices]


def stratified_sample(entries: Iterable[FactorCatalogEntry], count: int) -> list[FactorCatalogEntry]:
    groups: dict[str, list[FactorCatalogEntry]] = defaultdict(list)
    for entry in entries:
        if entry.enabled and entry.runnable:
            groups[entry.category].append(entry)
    if not groups:
        raise ValueError("no runnable factor candidates")
    if count > sum(map(len, groups.values())):
        raise ValueError("requested factor count exceeds runnable candidates")
    allocation = {category: 0 for category in groups}
    categories = sorted(groups)
    for _ in range(count):
        available = [category for category in categories if allocation[category] < len(groups[category])]
        category = min(available, key=lambda value: (allocation[value] / len(groups[value]), allocation[value], value))
        allocation[category] += 1
    selected: list[FactorCatalogEntry] = []
    for category in categories:
        selected.extend(evenly_spaced(groups[category], allocation[category]))
    return sorted(selected, key=lambda entry: (entry.category, entry.name))


def ensure_directions(
    selected: list[FactorCatalogEntry],
    candidates: Iterable[FactorCatalogEntry],
    required: Iterable[str],
) -> list[FactorCatalogEntry]:
    result = list(selected)
    all_candidates = sorted(candidates, key=lambda entry: (entry.category, entry.name))
    for direction in required:
        if any(entry.expected_direction == direction for entry in result):
            continue
        replacement = next(
            (entry for entry in all_candidates if entry.expected_direction == direction and entry not in result),
            None,
        )
        if replacement is None:
            raise ValueError(f"no runnable candidate for required direction: {direction}")
        replace_index = next(
            (index for index in range(len(result) - 1, -1, -1) if result[index].expected_direction == "watch"),
            None,
        )
        if replace_index is None:
            raise ValueError("cannot reserve required direction without changing factor count")
        result[replace_index] = replacement
    unique = {entry.name: entry for entry in result}
    if len(unique) != len(result):
        raise ValueError("direction reservation introduced a duplicate factor")
    return sorted(result, key=lambda entry: (entry.category, entry.name))
