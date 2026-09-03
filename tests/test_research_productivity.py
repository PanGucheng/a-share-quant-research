from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import yaml

import model_research.fast_research as fast_module
import model_research.research_cache as cache_module
from model_research.fast_research import (
    _profile_dates,
    _promotion_decision,
    _require_child_path,
    load_fast_research_config,
)
from model_research.feature_pool_experiment import run_development_arm
from model_research.inputs import InputAccessAudit
from model_research.linear_models import _validation_metrics
from model_research.research_cache import (
    build_preprocessing_fit_identity,
    build_projection_spool_identity,
    get_or_build_preprocessing_fit,
    get_or_build_projection_spools,
)


def _fake_context(tmp_path: Path) -> tuple[dict, object, object, Path]:
    partition = tmp_path / "matrix.parquet"
    pd.DataFrame({"datetime": ["2024-01-01"], "instrument": ["A"]}).to_parquet(
        partition, index=False
    )
    matrix = SimpleNamespace(
        factor_index={"f1": partition, "f2": partition},
        partition_receipts=(
            {
                "partition_path": partition.as_posix(),
                "recorded_sha256": "matrix-content",
                "observed_sha256": "matrix-content",
                "hash_verified": True,
            },
        ),
    )
    resolution = SimpleNamespace(
        manifests={
            "matrix": {
                "artifact_id": "matrix-v1",
                "factor_catalog_id": "catalog-v1",
            },
            "labels": {"artifact_id": "labels-v1"},
        }
    )
    protocol = {
        "target": {"label_id": "label", "minimum_daily_pairs": 1},
        "development_dry_run": {"date_batch_size": 40},
    }
    labels = tmp_path / "labels.bin"
    labels.write_bytes(b"labels-v1")
    return protocol, resolution, matrix, labels


def _fake_spool_fold(
    *,
    protocol_config,
    resolution,
    matrix,
    split_id,
    fold,
    dates,
    factors,
    output_dir,
    audit,
    timing_recorder,
):
    del protocol_config, resolution, matrix, split_id, timing_recorder
    audit.record(kind="feature", fold=fold)
    audit.record(kind="label", fold=fold)
    rows = []
    for date in dates:
        for instrument_index, instrument in enumerate(("A", "B")):
            row = {
                "datetime": date,
                "instrument": instrument,
                "__label": float(instrument_index),
                "__target": float(instrument_index) - 0.5,
                "__weight": 0.5,
            }
            row.update(
                {factor: float(index + instrument_index) for index, factor in enumerate(factors)}
            )
            rows.append(row)
    columns = ["datetime", "instrument", "__label", *factors, "__target", "__weight"]
    frame = pd.DataFrame(rows)[columns]
    path = output_dir / f"{fold}_000.parquet"
    frame.to_parquet(path, index=False)
    receipt = pd.DataFrame({"datetime": dates, "status": "pass"})
    return [path], receipt


def test_projection_spool_cache_hit_invalidation_corruption_and_parity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cache_module, "_spool_fold", _fake_spool_fold)
    protocol, resolution, matrix, labels = _fake_context(tmp_path)
    dates = pd.date_range("2024-01-01", periods=3)
    cache_root = tmp_path / "cache"
    first_audit = InputAccessAudit()
    first = get_or_build_projection_spools(
        cache_root=cache_root,
        protocol_config=protocol,
        resolution=resolution,
        matrix=matrix,
        split_id="split_001",
        fold="train",
        dates=dates,
        factors=["f1", "f2"],
        labels_path=labels,
        audit=first_audit,
    )
    assert first.cache_hit is False
    assert first_audit.test_read_count == 0
    expected = pd.concat([pd.read_parquet(path) for path in first.spool_paths])

    second_audit = InputAccessAudit()
    second = get_or_build_projection_spools(
        cache_root=cache_root,
        protocol_config=protocol,
        resolution=resolution,
        matrix=matrix,
        split_id="split_001",
        fold="train",
        dates=dates,
        factors=["f1", "f2"],
        labels_path=labels,
        audit=second_audit,
    )
    assert second.cache_hit is True
    assert second.cache_key == first.cache_key
    assert second_audit.feature_reads["train"] == 0
    pd.testing.assert_frame_equal(expected, pd.concat([pd.read_parquet(path) for path in second.spool_paths]))

    corrupt_path = second.spool_paths[0]
    corrupt_path.write_bytes(corrupt_path.read_bytes() + b"corrupt")
    rebuilt = get_or_build_projection_spools(
        cache_root=cache_root,
        protocol_config=protocol,
        resolution=resolution,
        matrix=matrix,
        split_id="split_001",
        fold="train",
        dates=dates,
        factors=["f1", "f2"],
        labels_path=labels,
        audit=InputAccessAudit(),
    )
    assert rebuilt.cache_status == "corrupt_rebuilt"
    pd.testing.assert_frame_equal(expected, pd.concat([pd.read_parquet(path) for path in rebuilt.spool_paths]))


def test_projection_spool_cache_identity_binds_all_high_risk_inputs(tmp_path: Path) -> None:
    protocol, resolution, matrix, labels = _fake_context(tmp_path)
    dates = pd.date_range("2024-01-01", periods=3)

    def identity(**changes):
        arguments = {
            "protocol_config": protocol,
            "resolution": resolution,
            "matrix": matrix,
            "split_id": "split_001",
            "fold": "train",
            "dates": dates,
            "factors": ["f1", "f2"],
            "labels_path": labels,
            "dtype": "float64",
        }
        arguments.update(changes)
        return build_projection_spool_identity(**arguments)["cache_key"]

    baseline = identity()
    assert identity(factors=["f2", "f1"]) != baseline
    assert identity(dates=pd.date_range("2024-01-02", periods=3)) != baseline
    assert identity(dtype="float32") != baseline
    changed_resolution = SimpleNamespace(
        manifests={**resolution.manifests, "matrix": {"artifact_id": "matrix-v2"}}
    )
    assert identity(resolution=changed_resolution) != baseline


def test_projection_cache_forbids_test_scope(tmp_path: Path) -> None:
    protocol, resolution, matrix, labels = _fake_context(tmp_path)
    with pytest.raises(PermissionError, match="forbids test scope"):
        build_projection_spool_identity(
            protocol_config=protocol,
            resolution=resolution,
            matrix=matrix,
            split_id="split_001",
            fold="test",
            dates=pd.date_range("2024-01-01", periods=2),
            factors=["f1"],
            labels_path=labels,
        )


def test_preprocessing_fit_cache_is_exact_scope_bound_and_corruption_safe(
    tmp_path: Path,
) -> None:
    _, _, _, _ = _fake_context(tmp_path)
    spool_dir = tmp_path / "spools"
    spool_dir.mkdir()
    spools, _ = _fake_spool_fold(
        protocol_config={},
        resolution=None,
        matrix=None,
        split_id="split_001",
        fold="train",
        dates=pd.date_range("2024-01-01", periods=3),
        factors=["f1", "f2"],
        output_dir=spool_dir,
        audit=InputAccessAudit(),
        timing_recorder=None,
    )
    cache_root = tmp_path / "preprocessing_cache"
    arguments = {
        "cache_root": cache_root,
        "spool_paths": spools,
        "factors": ["f1", "f2"],
        "fit_scope": "train",
        "preprocessing_config": {"imputation": "weighted_median"},
        "factor_batch_size": 2,
    }
    first = get_or_build_preprocessing_fit(**arguments)
    second = get_or_build_preprocessing_fit(**arguments)
    assert first.cache_hit is False
    assert second.cache_hit is True
    np.testing.assert_array_equal(first.preprocessing.medians, second.preprocessing.medians)
    np.testing.assert_array_equal(first.preprocessing.means, second.preprocessing.means)
    np.testing.assert_array_equal(first.preprocessing.variances, second.preprocessing.variances)

    train_key = build_preprocessing_fit_identity(
        **{key: value for key, value in arguments.items() if key != "cache_root"}
    )["cache_key"]
    final_key = build_preprocessing_fit_identity(
        **{
            key: ("train_plus_validation" if key == "fit_scope" else value)
            for key, value in arguments.items()
            if key != "cache_root"
        }
    )["cache_key"]
    assert train_key != final_key

    payload = second.manifest_path.parent / "preprocessing.npz"
    payload.write_bytes(payload.read_bytes() + b"corrupt")
    rebuilt = get_or_build_preprocessing_fit(**arguments)
    assert rebuilt.cache_status == "corrupt_rebuilt"
    np.testing.assert_array_equal(first.preprocessing.medians, rebuilt.preprocessing.medians)


def test_fast_profile_is_versioned_non_authoritative_and_test_inaccessible(
    tmp_path: Path,
) -> None:
    config_path = Path("configs/fast_research_v1.yaml")
    config = load_fast_research_config(config_path)
    assert config["execution_class"] == "exploratory_fast"
    for field in (
        "authoritative_execution",
        "selection_authorized",
        "production_model_selected",
        "strategy_v2_authorized",
    ):
        assert config[field] is False
    with pytest.raises(PermissionError, match="development folds"):
        _profile_dates(
            profile=config,
            protocol_config={},
            split_id="split_001",
            fold="test",
        )
    assert not hasattr(fast_module, "run_coordinated_historical_replay")
    assert "historical" not in inspect.signature(fast_module.run_fast_research_pair).parameters
    assert fast_module._validation_metrics is _validation_metrics
    changed = dict(config)
    changed["date_counts"] = {**config["date_counts"], "train": 121}
    changed_path = tmp_path / "changed_fast_profile.yaml"
    changed_path.write_text(yaml.safe_dump(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="new profile version"):
        load_fast_research_config(changed_path)


def test_fast_outputs_cannot_target_production_artifacts(tmp_path: Path) -> None:
    allowed = tmp_path / "outputs" / "research_productivity_v1" / "fast_runs"
    allowed.mkdir(parents=True)
    original_resolve = fast_module.resolve
    try:
        fast_module.resolve = lambda value: allowed if value == "allowed" else original_resolve(value)
        _require_child_path(allowed / "run_001", "allowed", "output")
        with pytest.raises(ValueError, match="non-authoritative root"):
            _require_child_path(tmp_path / "artifacts" / "strategy_v2", "allowed", "output")
    finally:
        fast_module.resolve = original_resolve


def test_promotion_is_only_a_resource_gate() -> None:
    profile = load_fast_research_config(Path("configs/fast_research_v1.yaml"))
    deltas = pd.DataFrame({"mean_daily_rank_ic_delta": [0.01, 0.02]})
    status, reason = _promotion_decision(deltas, profile)
    assert status == "promote_to_full"
    assert "resource_gate" in reason
    receipt_contract = {
        "promotion_is_scientific_winner": False,
        "production_model_selected": False,
        "strategy_v2_authorized": False,
    }
    assert json.dumps(receipt_contract)


def test_full_development_runner_contract_remains_cache_off() -> None:
    parameters = inspect.signature(run_development_arm).parameters
    assert "cache_root" not in parameters
    assert parameters["execution_profile"].default == "ml_feature_pool_mvp_v1"
    assert parameters["freeze_metadata"].default is None
