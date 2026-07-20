from __future__ import annotations

from factor_research.catalog import FactorCatalogEntry
from research_validation.factor_trial import ensure_directions, evenly_spaced, stratified_sample


def entry(name: str, category: str, direction: str = "watch") -> FactorCatalogEntry:
    return FactorCatalogEntry(name, category, "source", "file", "fn", "sha", "MIT", direction, ("$close",), ("label",), "stage", True, True, "adapter", name)


def test_even_sample_is_deterministic_and_spans_candidates() -> None:
    values = [entry(f"f{index:02d}", "price") for index in range(10)]
    assert [item.name for item in evenly_spaced(values, 3)] == ["f01", "f05", "f08"]


def test_stratified_sample_balances_categories_without_metrics() -> None:
    values = [entry(f"p{index}", "price") for index in range(8)] + [entry(f"v{index}", "volume") for index in range(2)]
    selected = stratified_sample(values, 4)
    assert len(selected) == 4
    assert {item.category for item in selected} == {"price", "volume"}


def test_required_positive_and_negative_directions_are_reserved() -> None:
    values = [entry(f"w{index}", "basic") for index in range(8)]
    values += [entry("positive", "basic", "positive"), entry("negative", "basic", "negative")]
    selected = ensure_directions(stratified_sample(values, 5), values, ["positive", "negative"])
    assert {item.expected_direction for item in selected} >= {"positive", "negative"}
    assert len({item.name for item in selected}) == 5
