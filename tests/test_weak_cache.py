from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from factor_research.evaluator import (
    FactorResearchConfig,
    feature_cache_fingerprint,
    feature_cache_path,
    load_feature_frame,
)
from factor_research.expression_adapter import (
    ExpressionFrameConfig,
    expression_chunk_cache_fingerprint,
    expression_frame_cache_fingerprint,
    expression_frame_cache_path,
)
from qlib_baseline.cache import (
    build_cache_fingerprint,
    cache_metadata_path,
    cache_path,
    normalized_source_ast_hash,
    provider_data_fingerprint,
    read_dataframe_cache,
    select_provider_fingerprint_fields,
    write_dataframe_cache,
)
from scripts.run_factor_research_v3 import ResearchWindow, basic_factor_cache_path


def _provider(root: Path) -> Path:
    (root / "calendars").mkdir(parents=True)
    (root / "instruments").mkdir()
    (root / "features" / "sh600000").mkdir(parents=True)
    (root / "calendars" / "day.txt").write_text(
        "2020-01-02\n2020-01-03\n", encoding="utf-8"
    )
    (root / "instruments" / "demo.txt").write_text(
        "sh600000\t2020-01-02\t2020-01-03\n",
        encoding="utf-8",
    )
    for field in ("open", "high", "low", "close", "volume", "amount"):
        (root / "features" / "sh600000" / f"{field}.day.bin").write_bytes(
            field.encode()
        )
    return root


def _feature_config(provider: Path, cache_dir: Path) -> FactorResearchConfig:
    return FactorResearchConfig(
        provider_uri=provider.as_posix(),
        market="demo",
        start_time="2020-01-02",
        end_time="2020-01-03",
        output_dir=cache_dir / "output",
        feature_cache_dir=cache_dir,
    )


def _expression_config(provider: Path, output_dir: Path) -> ExpressionFrameConfig:
    return ExpressionFrameConfig(
        provider_uri=provider.as_posix(),
        market="demo",
        start="2020-01-02",
        end="2020-01-03",
        max_instruments=None,
        catalog_path=output_dir / "catalog.yaml",
        inventory_path=output_dir / "inventory.csv",
        output_dir=output_dir,
    )


def test_normalized_ast_ignores_comments_formatting_and_docstrings() -> None:
    compact = """
def calculate(value):
    return value + 1
"""
    formatted = """
def calculate(value):
    \"\"\"Documentation is not computation.\"\"\"
    # A comment must not invalidate a data cache.
    return (value + 1)
"""
    changed = """
def calculate(value):
    return value + 2
"""

    assert normalized_source_ast_hash(compact) == normalized_source_ast_hash(formatted)
    assert normalized_source_ast_hash(compact) != normalized_source_ast_hash(changed)


def test_each_fingerprint_layer_invalidates_cache_key() -> None:
    base = build_cache_fingerprint(
        "example",
        data={"snapshot": "a"},
        computation={"formula": "x + 1"},
        request={"fields": ["x"]},
    )
    changes = [
        build_cache_fingerprint(
            "example",
            data={"snapshot": "b"},
            computation={"formula": "x + 1"},
            request={"fields": ["x"]},
        ),
        build_cache_fingerprint(
            "example",
            data={"snapshot": "a"},
            computation={"formula": "x + 2"},
            request={"fields": ["x"]},
        ),
        build_cache_fingerprint(
            "example",
            data={"snapshot": "a"},
            computation={"formula": "x + 1"},
            request={"fields": ["x", "y"]},
        ),
    ]

    assert all(item["cache_key"] != base["cache_key"] for item in changes)
    assert set(base["component_hashes"]) == {
        "cache_schema",
        "data_fingerprint",
        "computation_fingerprint",
        "request_fingerprint",
    }


def test_provider_snapshot_detects_relevant_data_mutation(tmp_path: Path) -> None:
    provider = _provider(tmp_path / "provider")
    before = provider_data_fingerprint(provider, market="demo", fields=["$close"])
    feature = provider / "features" / "sh600000" / "close.day.bin"
    feature.write_bytes(feature.read_bytes() + b"changed")
    after = provider_data_fingerprint(provider, market="demo", fields=["$close"])

    assert before["calendar"]["sha256"]
    assert before["instruments"]["sha256"]
    assert (
        before["feature_content_inventory_sha256"]
        != after["feature_content_inventory_sha256"]
    )


def test_unavailable_provider_still_normalizes_requested_fields(tmp_path: Path) -> None:
    snapshot = provider_data_fingerprint(
        tmp_path / "missing",
        market="demo",
        fields=["$Close"],
    )

    assert select_provider_fingerprint_fields(snapshot, ["$close"])["fields"] == [
        "close"
    ]


def test_parquet_cache_requires_matching_sidecar(tmp_path: Path) -> None:
    fingerprint = build_cache_fingerprint(
        "frame",
        data={"snapshot": "a"},
        computation={"formula": "x"},
        request={"fields": ["x"]},
    )
    path = cache_path(tmp_path, "frame", fingerprint)
    frame = pd.DataFrame({"x": [1.0, 2.0]})
    write_dataframe_cache(
        path,
        frame,
        fingerprint,
        diagnostics={"producer_code_sha": "diagnostic-only"},
    )

    pd.testing.assert_frame_equal(read_dataframe_cache(path, fingerprint), frame)
    metadata = json.loads(cache_metadata_path(path).read_text(encoding="utf-8"))
    assert metadata["diagnostics"]["producer_code_sha"] == "diagnostic-only"

    other = build_cache_fingerprint(
        "frame",
        data={"snapshot": "other"},
        computation={"formula": "x"},
        request={"fields": ["x"]},
    )
    assert read_dataframe_cache(path, other) is None
    cache_metadata_path(path).unlink()
    assert read_dataframe_cache(path, fingerprint) is None


def test_evaluator_uses_new_cache_and_ignores_legacy_pickle(tmp_path: Path) -> None:
    provider = _provider(tmp_path / "provider")
    cache_dir = tmp_path / "cache"
    config = _feature_config(provider, cache_dir)
    fingerprint = feature_cache_fingerprint(config)
    path = feature_cache_path(config)
    assert path is not None
    assert path.suffix == ".parquet"

    legacy = cache_dir / "features_legacy.pkl"
    legacy.parent.mkdir(parents=True)
    pd.DataFrame({"legacy": [True]}).to_pickle(legacy)
    expected = pd.DataFrame(
        {
            "instrument": ["SH600000"],
            "datetime": [pd.Timestamp("2020-01-02")],
            "$open": [1.0],
        }
    )
    write_dataframe_cache(path, expected, fingerprint, diagnostics={})

    pd.testing.assert_frame_equal(load_feature_frame(config), expected)
    assert legacy.is_file()


def test_expression_cache_key_binds_formula_and_uses_parquet(tmp_path: Path) -> None:
    provider = _provider(tmp_path / "provider")
    config = _expression_config(provider, tmp_path / "output")
    table = pd.DataFrame(
        {
            "catalog_name": ["alpha"],
            "factor_name": ["Alpha"],
            "category": ["test"],
            "expression": ["Mean($close, 5)"],
            "field_status": ["available"],
        }
    )
    changed = table.assign(expression="Mean($close, 10)")

    assert expression_frame_cache_path(config, table).suffix == ".parquet"
    assert (
        expression_frame_cache_fingerprint(config, table)["cache_key"]
        != expression_frame_cache_fingerprint(config, changed)["cache_key"]
    )


def test_expression_chunk_ignores_unrequested_provider_field_mutation(
    tmp_path: Path,
) -> None:
    provider = _provider(tmp_path / "provider")
    config = _expression_config(provider, tmp_path / "output")
    table = pd.DataFrame(
        {
            "catalog_name": ["close_factor", "volume_factor"],
            "factor_name": ["Close", "Volume"],
            "category": ["test", "test"],
            "expression": ["Mean($close, 5)", "Mean($volume, 5)"],
            "field_status": ["available", "available"],
        }
    )
    close_only = table.iloc[[0]].reset_index(drop=True)
    before_snapshot = provider_data_fingerprint(
        provider,
        market="demo",
        fields=["$close", "$volume"],
    )
    before = expression_chunk_cache_fingerprint(
        config,
        close_only,
        1,
        provider_snapshot=before_snapshot,
    )
    volume = provider / "features" / "sh600000" / "volume.day.bin"
    volume.write_bytes(volume.read_bytes() + b"changed")
    after_snapshot = provider_data_fingerprint(
        provider,
        market="demo",
        fields=["$close", "$volume"],
    )
    after = expression_chunk_cache_fingerprint(
        config,
        close_only,
        1,
        provider_snapshot=after_snapshot,
    )

    assert before["cache_key"] == after["cache_key"]


def test_v3_basic_factor_cache_uses_layered_parquet_key(tmp_path: Path) -> None:
    provider = _provider(tmp_path / "provider")
    args = argparse.Namespace(
        provider_uri=provider.as_posix(),
        market="demo",
        labels=["label_20d_t1"],
        quantiles=5,
        min_count=2,
        no_feature_cache=False,
        feature_cache_dir=tmp_path / "features",
        refresh_feature_cache=False,
        no_factor_cache=False,
        factor_cache_dir=tmp_path / "factors",
    )
    window = ResearchWindow(
        "fixture",
        "2020-01-02",
        "2020-01-03",
        tmp_path / "tradability",
        tmp_path / "quality",
    )

    path = basic_factor_cache_path(args, window)
    assert path is not None
    assert path.suffix == ".parquet"
    assert path.name.startswith("basic_factors_")
