from __future__ import annotations

from pathlib import Path
import json
import shutil

import numpy as np
import pandas as pd
import pytest
import yaml

from research_validation.lineage import (
    CodeState,
    sha256_file,
    write_stage_artifact_manifest,
)
from model_research.freeze import load_freeze_before_test
from model_research.gates import (
    ModelScopeBlockedError,
    assert_research_model_entry_artifact,
    assert_research_model_entry_file,
    assert_model_scope_allowed,
)
from model_research.inputs import (
    InputAccessAudit,
    assert_feature_order,
    assert_fold_isolation,
)
from model_research.lineage import (
    AuthoritativeParentPaths,
    resolve_authoritative_parents,
    resolve_matrix_runtime_authority,
)
from model_research.linear_models import (
    _candidate_grid,
    _select_candidate,
    _validation_metrics,
    load_linear_config,
)
from model_research.lightgbm_models import (
    candidate_grid as lightgbm_candidate_grid,
    load_lightgbm_config,
)
from model_research.linear_execution import load_linear_execution_config
from model_research.preprocessing import (
    daily_equal_weights,
    fit_weighted_preprocessing,
    stable_weighted_median,
)
from model_research.protocol import parent_paths
from model_research.protocol_v1_1 import build_protocol_binding
from model_research.schemas import (
    PREDICTION_COLUMNS,
    freeze_schema_missing,
    prediction_schema_violations,
)
from model_research.targets import (
    daily_cross_sectional_rank_centered,
    eligible_daily_cross_sectional_rank_centered,
)


ROOT = Path(__file__).resolve().parents[1]


def ready_scope(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "research_model_protocol_ready": True,
        "research_model_input_ready": True,
        "research_model_training_ready": True,
        "research_model_hard_stop_active": False,
        "production_model_hard_stop_active": True,
        "production_model_selected": False,
    }
    values.update(overrides)
    return values


@pytest.mark.parametrize(
    "experiment_class",
    [None, "", "authoritative_oos", "production", "paper", "live", "other"],
)
def test_scope_gate_rejects_unspecified_production_and_unknown(
    experiment_class: str | None,
) -> None:
    with pytest.raises(ModelScopeBlockedError):
        assert_model_scope_allowed(
            ready_scope(),
            experiment_class=experiment_class,
        )


def test_scope_gate_allows_only_ready_post_observation_research() -> None:
    assert_model_scope_allowed(
        ready_scope(),
        experiment_class="post_observation_research",
    )
    with pytest.raises(
        ModelScopeBlockedError, match="research_model_input_ready=false"
    ):
        assert_model_scope_allowed(
            ready_scope(research_model_input_ready=False),
            experiment_class="post_observation_research",
        )


def test_authoritative_parent_resolution_rejects_legacy_direct_parent(
    tmp_path: Path,
) -> None:
    source = ROOT / "outputs/date_split_semantics_v1/current/artifact_manifest.json"
    legacy = tmp_path / "artifact_manifest.json"
    payload = source.read_text(encoding="utf-8").replace(
        '"stage_id": "date_split_semantics_v1"',
        '"stage_id": "purged_walk_forward_v1"',
    )
    legacy.write_text(payload, encoding="utf-8")
    paths = authoritative_paths()
    with pytest.raises(ValueError, match="date_stage_mismatch"):
        resolve_authoritative_parents(
            AuthoritativeParentPaths(
                date_manifest=legacy,
                selection_manifest=paths.selection_manifest,
                matrix_manifest=paths.matrix_manifest,
                labels_manifest=paths.labels_manifest,
                universe_manifest=paths.universe_manifest,
                date_assignments=paths.date_assignments,
                selection_date_assignments=paths.selection_date_assignments,
            )
        )


def authoritative_paths() -> AuthoritativeParentPaths:
    return AuthoritativeParentPaths(
        date_manifest=ROOT
        / "outputs/date_split_semantics_v1/current/artifact_manifest.json",
        selection_manifest=ROOT
        / "outputs/research_selection_lineage_closure_v1/current/artifact_manifest.json",
        matrix_manifest=ROOT
        / "outputs/full_research_feature_matrix_v4/current/artifact_manifest.json",
        labels_manifest=ROOT
        / "outputs/full_research_labels_v2/current/artifact_manifest.json",
        universe_manifest=ROOT
        / "outputs/point_in_time_universe_v2/full_research/artifact_manifest.json",
        date_assignments=ROOT
        / "outputs/date_split_semantics_v1/current/date_assignments.csv",
        selection_date_assignments=ROOT
        / "outputs/research_selection_lineage_closure_v1/current/date_assignments.csv",
    )


def test_authoritative_parent_resolution_uses_date_wrapper_and_closure() -> None:
    resolved = resolve_authoritative_parents(authoritative_paths())
    assert len(resolved.receipts) == 5
    assert resolved.manifests["date"]["stage_id"] == "date_split_semantics_v1"
    assert resolved.manifests["selection"]["stage_id"] == (
        "research_selection_lineage_closure_v1"
    )


def test_matrix_runtime_is_resolved_from_authoritative_manifest(
    tmp_path: Path,
) -> None:
    current_dir = tmp_path / "current"
    runtime_dir = tmp_path / "runtime"
    current_dir.mkdir()
    runtime_dir.mkdir()
    factor_name = "alpha158_CNTD30"
    partition_path = runtime_dir / "batch_000.parquet"
    pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "instrument": ["SH600000", "SH600000"],
            factor_name: [0.1, 0.2],
        }
    ).to_parquet(partition_path, index=False)
    resolved_config_path = current_dir / "resolved_config.json"
    resolved_config = {
        "profile_name": "full_research",
        "profile_type": "full_research",
        "research_run_family_id": "matrix-runtime-unit-test",
        "output_dir": current_dir.as_posix(),
        "runtime_dir": runtime_dir.as_posix(),
    }
    resolved_config_path.write_text(
        json.dumps(resolved_config, sort_keys=True),
        encoding="utf-8",
    )
    partition_status_path = current_dir / "partition_status.csv"
    pd.DataFrame(
        [
            {
                "batch_id": "batch_000",
                "status": "pass",
                "output_path": partition_path.as_posix(),
                "output_sha256": sha256_file(partition_path),
            }
        ]
    ).to_csv(partition_status_path, index=False)
    write_stage_artifact_manifest(
        project_root=ROOT,
        stage_id="full_research_feature_matrix_v4",
        config=resolved_config,
        output_dir=current_dir,
        output_files=[resolved_config_path, partition_status_path],
        code_state=CodeState(
            commit_sha="unit-test",
            dirty=False,
            diff_sha256="",
        ),
        universe_artifact_id="universe:unit-test",
        factor_catalog_id="catalog:unit-test",
        factor_frame_id="frame:unit-test",
        start_date="2024-01-02",
        end_date="2024-01-03",
    )

    runtime = resolve_matrix_runtime_authority(
        project_root=ROOT,
        matrix_manifest_path=current_dir / "artifact_manifest.json",
        selected_factors=[factor_name],
        verify_selected_partition_hashes=True,
    )
    assert runtime.partition_status_path == partition_status_path
    assert runtime.factor_index[factor_name] == partition_path
    assert runtime.runtime_dir == runtime_dir
    assert runtime.partition_receipts[0]["hash_verified"] is True


def test_linear_model_config_freezes_candidate_counts_and_rejects_auto(
    tmp_path: Path,
) -> None:
    source = ROOT / "configs/research_linear_models_v1.yaml"
    config = yaml.safe_load(source.read_text(encoding="utf-8"))
    assert load_linear_config(source)["validation"]["primary_metric"] == (
        "mean_daily_rank_ic"
    )
    config["ridge"]["solver"] = "auto"
    rejected = tmp_path / "linear.yaml"
    rejected.write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="solver=auto"):
        load_linear_config(rejected)


def test_linear_candidate_grid_and_metric_tie_breaks_are_frozen() -> None:
    config = load_linear_config(
        ROOT / "configs/research_linear_models_v1.yaml"
    )
    ridge = _candidate_grid(
        config,
        method="ridge",
        solver="lsqr",
        limit=None,
    )
    elastic = _candidate_grid(
        config,
        method="elastic_net",
        solver="lsqr",
        limit=None,
    )
    assert len(ridge) == 5
    assert len(elastic) == 15
    assert all(candidate["solver"] != "auto" for candidate in ridge)
    metrics = pd.DataFrame(
        [
            {
                **ridge[0],
                "mean_daily_rank_ic": 0.01,
                "daily_rank_ic_ir": 0.2,
                "prediction_coverage": 1.0,
                "nonzero_coefficient_count": 2,
                "status": "pass",
            },
            {
                **ridge[-1],
                "mean_daily_rank_ic": 0.01,
                "daily_rank_ic_ir": 0.2,
                "prediction_coverage": 1.0,
                "nonzero_coefficient_count": 2,
                "status": "pass",
            },
        ]
    )
    assert float(_select_candidate(metrics, method="ridge")["alpha"]) == 100.0


def test_linear_execution_config_keeps_corrected_semantics() -> None:
    config = load_linear_execution_config(
        ROOT / "configs/research_linear_execution_v1.yaml"
    )
    assert config["methods"] == ["ridge", "elastic_net"]
    assert config["execution"]["signal_lag_trading_days"] == 1
    assert config["execution"]["strict_t_plus_one"] is True
    assert config["execution"]["dynamic_lot_rules"] is True
    assert config["market_cache_manifest"].startswith(
        "outputs/market_cache_v3/"
    )
    assert config["execution"]["maximum_stale_valuation_days"] == 20


def test_lightgbm_candidate_protocol_is_fixed_and_bounded() -> None:
    config = load_lightgbm_config(
        ROOT / "configs/research_lightgbm_v1.yaml"
    )
    candidates = lightgbm_candidate_grid(config)
    assert len(candidates) == 16
    assert len({row["candidate_sha256"] for row in candidates}) == 16
    assert {row["num_boost_round"] for row in candidates} == {
        100,
        200,
        400,
        800,
    }
    assert config["early_stopping"] is False
    assert config["trainer_metric_authority"] == "diagnostic_only"
    assert config["determinism"]["num_threads"] == 1
    assert config["resource_canary"]["checkpoints"] == [100, 200, 400, 800]
    assert len(config["resource_canary"]["structural_row_ids"]) == 4


def test_linear_validation_metric_is_daily_rank_ic() -> None:
    metadata = pd.DataFrame(
        {
            "datetime": pd.to_datetime(
                ["2024-01-02"] * 3 + ["2024-01-03"] * 3
            ),
            "instrument": ["a", "b", "c", "a", "b", "c"],
            "__label": [1.0, 2.0, 3.0, 3.0, 2.0, 1.0],
        }
    )
    result = _validation_metrics(
        metadata,
        np.asarray([1.0, 2.0, 3.0, 3.0, 2.0, 1.0]),
    )
    assert result["mean_daily_rank_ic"] == pytest.approx(1.0)
    assert result["prediction_coverage"] == 1.0
    constant = _validation_metrics(metadata, np.ones(len(metadata)))
    assert constant["daily_ic_count"] == 0
    assert constant["mean_daily_rank_ic"] == float("-inf")


def test_weighted_preprocessing_is_daily_equal_and_order_stable() -> None:
    dates = np.asarray(["a", "a", "b"])
    weights = daily_equal_weights(dates)
    assert np.allclose(weights, [0.5, 0.5, 1.0])
    assert stable_weighted_median(
        np.asarray([2.0, 1.0, 100.0]),
        weights,
        canonical_keys=np.asarray(["b", "a", "c"]),
    ) == 2.0
    fit = fit_weighted_preprocessing(
        np.asarray([[1.0, np.nan], [3.0, 2.0], [5.0, 8.0]]),
        weights,
        feature_names=("f1", "f2"),
        canonical_row_keys=np.asarray(["a", "b", "c"]),
    )
    transformed = fit.transform(np.asarray([[2.0, np.nan]]))
    assert transformed.shape == (1, 2)


def test_weighted_preprocessing_blocks_all_nan_and_near_zero_variance() -> None:
    with pytest.raises(ValueError, match="entirely NaN"):
        fit_weighted_preprocessing(
            np.asarray([[1.0, np.nan], [2.0, np.nan]]),
            np.ones(2),
            feature_names=("f1", "f2"),
            canonical_row_keys=np.asarray(["a", "b"]),
        )
    with pytest.raises(ValueError, match="near-zero"):
        fit_weighted_preprocessing(
            np.asarray([[1.0], [1.0]]),
            np.ones(2),
            feature_names=("f1",),
            canonical_row_keys=np.asarray(["a", "b"]),
        )


def test_prediction_and_freeze_schemas_are_fail_closed() -> None:
    assert prediction_schema_violations(list(PREDICTION_COLUMNS)) == []
    assert prediction_schema_violations(
        list(PREDICTION_COLUMNS) + ["label_20d_t1"]
    )
    assert "environment_lock_sha256" in freeze_schema_missing({})


def test_test_loader_requires_freeze_artifact(tmp_path: Path) -> None:
    with pytest.raises(PermissionError, match="missing pre-test freeze"):
        load_freeze_before_test(tmp_path / "pre_test_freeze_manifest.json")


def test_feature_order_and_fold_overlap_fail_closed() -> None:
    with pytest.raises(ValueError, match="feature order mismatch"):
        assert_feature_order(["f2", "f1"], ["f1", "f2"])
    train = pd.DatetimeIndex(["2024-01-02", "2024-01-03"])
    validation = pd.DatetimeIndex(["2024-01-03"])
    test = pd.DatetimeIndex(["2024-02-01"])
    with pytest.raises(ValueError, match="assignments overlap"):
        assert_fold_isolation(train, validation, test)


def test_target_transform_uses_daily_rank_and_blocks_small_days() -> None:
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(
                ["2024-01-02"] * 3 + ["2024-01-03"] * 2
            ),
            "label": [1.0, 2.0, 3.0, 1.0, 2.0],
        }
    )
    transformed, receipt = daily_cross_sectional_rank_centered(
        frame,
        label_column="label",
        minimum_daily_pairs=3,
    )
    assert transformed.iloc[:3].notna().all()
    assert transformed.iloc[3:].isna().all()
    assert receipt["status"].tolist() == [
        "pass",
        "blocked_insufficient_daily_pairs",
    ]


def test_target_v2_ranks_only_final_eligible_sample_and_records_zero_dates() -> None:
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(
                ["2024-01-02"] * 4 + ["2024-01-03"]
            ),
            "instrument": ["a", "b", "c", "d", "a"],
            "f1": [1.0, 2.0, 3.0, np.nan, np.nan],
            "label": [1.0, 2.0, 100.0, -100.0, np.nan],
        }
    )
    transformed, eligible, receipt = (
        eligible_daily_cross_sectional_rank_centered(
            frame,
            label_column="label",
            feature_columns=["f1"],
            expected_dates=pd.DatetimeIndex(
                ["2024-01-02", "2024-01-03", "2024-01-04"]
            ),
            minimum_daily_pairs=3,
        )
    )
    assert eligible.tolist() == [True, True, True, False, False]
    assert np.allclose(
        transformed.iloc[:3].to_numpy(),
        [-1 / 6, 1 / 6, 0.5],
    )
    assert transformed.iloc[3:].isna().all()
    assert receipt["valid_pair_count"].tolist() == [3, 0, 0]
    assert receipt["status"].tolist() == [
        "pass",
        "blocked_insufficient_daily_pairs",
        "blocked_insufficient_daily_pairs",
    ]


def test_access_audit_starts_with_zero_test_reads() -> None:
    audit = InputAccessAudit()
    audit.record(kind="feature", fold="train")
    audit.record(kind="label", fold="validation")
    assert audit.test_read_count == 0


def test_direct_readiness_file_entry_is_always_forbidden(
    tmp_path: Path,
) -> None:
    readiness = tmp_path / "readiness.csv"
    pd.DataFrame([ready_scope()]).to_csv(readiness, index=False)
    with pytest.raises(ModelScopeBlockedError, match="direct readiness CSV"):
        assert_research_model_entry_file(
            readiness,
            experiment_class="post_observation_research",
        )


def test_artifact_entry_rejects_missing_and_legacy_v1_manifest(
    tmp_path: Path,
) -> None:
    with pytest.raises(ModelScopeBlockedError, match="missing protocol manifest"):
        assert_research_model_entry_artifact(
            tmp_path / "artifact_manifest.json",
            experiment_class="post_observation_research",
        )
    with pytest.raises(ModelScopeBlockedError, match="stage_id="):
        assert_research_model_entry_artifact(
            ROOT
            / "outputs/research_model_protocol_v1/current/artifact_manifest.json",
            experiment_class="production",
        )


def test_v1_1_binding_changes_for_protocol_mutation() -> None:
    config = yaml.safe_load(
        (
            ROOT / "configs/research_model_protocol_v1_1.yaml"
        ).read_text(encoding="utf-8")
    )
    resolution = resolve_authoritative_parents(parent_paths(config))
    baseline = build_protocol_binding(config, resolution)
    mutated = yaml.safe_load(yaml.safe_dump(config))
    mutated["target"]["minimum_daily_pairs"] = 101
    changed = build_protocol_binding(mutated, resolution)
    assert changed["base_protocol_sha256"] != baseline["base_protocol_sha256"]
    assert (
        changed["policy_section_sha256"]["target"]
        != baseline["policy_section_sha256"]["target"]
    )


def test_v1_1_artifact_entry_accepts_verified_current_and_rejects_tamper(
    tmp_path: Path,
) -> None:
    source = ROOT / "outputs/research_model_protocol_v1_1/current"
    manifest_path = source / "artifact_manifest.json"
    if not manifest_path.is_file():
        pytest.skip("V1.1 compact artifact is published later in the implementation")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if bool(manifest.get("code_dirty")):
        pytest.skip("local pre-publication artifact is intentionally dirty")
    assert_research_model_entry_artifact(
        manifest_path,
        experiment_class="post_observation_research",
    )
    tampered = tmp_path / "current"
    shutil.copytree(source, tampered)
    readiness_path = tampered / "readiness_summary.csv"
    readiness = pd.read_csv(readiness_path)
    readiness.loc[0, "authoritative_execution"] = True
    readiness.to_csv(readiness_path, index=False)
    with pytest.raises(ModelScopeBlockedError, match="output_hash_mismatch"):
        assert_research_model_entry_artifact(
            tampered / "artifact_manifest.json",
            experiment_class="post_observation_research",
        )
