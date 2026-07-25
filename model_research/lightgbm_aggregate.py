from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from research_validation.feature_matrix import canonical_hash, file_sha256
from research_validation.lineage import (
    capture_code_state,
    load_artifact_manifest,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher

from .freeze import validate_pre_test_freeze
from .gates import assert_research_model_entry_artifact
from .lightgbm_models import STAGE_ID, _contract
from .protocol import PROJECT_ROOT, resolve


PARENT_SPECS = (
    (
        "split_001",
        "outputs/research_lightgbm_v1/split_001/"
        "artifact_manifest.json",
    ),
    (
        "remaining",
        "outputs/research_lightgbm_v1/remaining/"
        "artifact_manifest.json",
    ),
)
FRAME_FILES = (
    "hyperparameter_candidate_manifest.csv",
    "validation_metrics.csv",
    "model_receipt.csv",
    "preprocessing_receipt.csv",
    "feature_importance.csv",
    "sample_eligibility_receipt.csv",
    "mutation_results.csv",
    "resource_summary.csv",
)
OUTPUTS = (
    "artifact_manifest.json",
    "resolved_config.json",
    "parent_receipts.csv",
    *FRAME_FILES,
    "selected_hyperparameters.json",
    "access_audit.csv",
    "contract_status.csv",
    "readiness_summary.csv",
    "run_report.md",
    "pre_test_freezes/split_001_lightgbm.json",
    "pre_test_freezes/split_002_lightgbm.json",
    "pre_test_freezes/split_003_lightgbm.json",
)


def aggregate_lightgbm_development(
    config: dict[str, Any],
    *,
    output_dir: Path,
    command: str,
) -> dict[str, Any]:
    protocol_manifest_path = resolve(config["protocol_manifest"])
    assert_research_model_entry_artifact(
        protocol_manifest_path,
        experiment_class=str(config["experiment_class"]),
        operation="training",
    )
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError(
            "LightGBM aggregation requires clean committed code"
        )
    parents: list[tuple[str, Path, dict[str, Any]]] = []
    for role, value in PARENT_SPECS:
        path = resolve(value)
        manifest = load_artifact_manifest(path)
        issues = validate_manifest_outputs(manifest, path.parent)
        if (
            manifest.get("stage_id") != STAGE_ID
            or manifest.get("artifact_status") != "pass"
            or manifest.get("lineage_status") != "complete"
            or issues
        ):
            raise ValueError(
                f"invalid LightGBM development parent: {role}: {issues}"
            )
        parents.append((role, path, manifest))

    frames: dict[str, pd.DataFrame] = {}
    for filename in FRAME_FILES:
        values: list[pd.DataFrame] = []
        for role, path, _ in parents:
            frame = pd.read_csv(path.parent / filename)
            frame.insert(0, "source_evidence", role)
            values.append(frame)
        frames[filename] = pd.concat(values, ignore_index=True)
    selected: dict[str, Any] = {}
    freezes: dict[str, dict[str, Any]] = {}
    access_values: list[pd.DataFrame] = []
    for role, path, _ in parents:
        payload = json.loads(
            (path.parent / "selected_hyperparameters.json").read_text(
                encoding="utf-8"
            )
        )
        if set(selected) & set(payload):
            raise ValueError("duplicate LightGBM selected split")
        selected.update(payload)
        for freeze_path in sorted(
            (path.parent / "pre_test_freezes").glob("*.json")
        ):
            if freeze_path.name in freezes:
                raise ValueError("duplicate LightGBM pre-test freeze")
            freeze = json.loads(
                freeze_path.read_text(encoding="utf-8")
            )
            validate_pre_test_freeze(freeze)
            freezes[freeze_path.name] = freeze
        access = pd.read_csv(path.parent / "access_audit.csv")
        access["source_evidence"] = role
        access_values.append(access)

    models = frames["model_receipt.csv"]
    preprocessing = frames["preprocessing_receipt.csv"]
    model_hashes_valid = all(
        Path(str(row.runtime_path)).is_file()
        and file_sha256(Path(str(row.runtime_path)))
        == str(row.model_binary_sha256)
        for row in models.itertuples(index=False)
    )
    preprocessing_hashes_valid = all(
        Path(str(row.runtime_path)).is_file()
        and file_sha256(Path(str(row.runtime_path)))
        == str(row.preprocessing_sha256)
        for row in preprocessing.itertuples(index=False)
    )
    expected_splits = {"split_001", "split_002", "split_003"}
    observed_splits = set(models["outer_split_id"].astype(str))
    candidate_counts = (
        frames["hyperparameter_candidate_manifest.csv"]
        .groupby("outer_split_id")
        .size()
        .to_dict()
    )
    candidate_counts_valid = all(
        int(candidate_counts.get(split_id, 0)) == 16
        for split_id in expected_splits
    )
    expected_freezes = {
        f"{split_id}_lightgbm.json" for split_id in expected_splits
    }
    freezes_valid = set(freezes) == expected_freezes
    freeze_hashes_valid = all(
        payload["model_binary_sha256"]
        == str(
            models.loc[
                models["outer_split_id"].astype(str).eq(
                    str(payload["outer_split_id"])
                ),
                "model_binary_sha256",
            ].iloc[0]
        )
        for payload in freezes.values()
    )
    access_detail = pd.concat(access_values, ignore_index=True)
    access = (
        access_detail.groupby(
            ["input_kind", "fold"], as_index=False
        )["read_count"]
        .sum()
        .sort_values(["input_kind", "fold"], kind="stable")
    )
    test_reads = int(
        access.loc[
            access["fold"].astype(str).eq("test"), "read_count"
        ].sum()
    )
    mutations = frames["mutation_results.csv"]
    contracts = pd.DataFrame(
        [
            _contract(
                "lightgbm_split_coverage_exact",
                observed_splits == expected_splits,
                sorted(observed_splits),
                sorted(expected_splits),
            ),
            _contract(
                "candidate_grid_exact",
                candidate_counts_valid,
                candidate_counts,
                "16 candidates per split",
            ),
            _contract(
                "validation_mutation_sensitive",
                len(mutations) == 3
                and mutations["status"].eq("pass").all(),
                mutations["status"].tolist(),
                "3 pass",
            ),
            _contract(
                "model_binary_hash_valid",
                model_hashes_valid,
                model_hashes_valid,
                True,
            ),
            _contract(
                "fitted_preprocessing_hash_valid",
                preprocessing_hashes_valid,
                preprocessing_hashes_valid,
                True,
            ),
            _contract(
                "pre_test_freeze_valid",
                freezes_valid and freeze_hashes_valid,
                {
                    "freeze_count": len(freezes),
                    "model_hashes_valid": freeze_hashes_valid,
                },
                {"freeze_count": 3, "model_hashes_valid": True},
            ),
            _contract(
                "test_read_count_before_freeze_zero",
                test_reads == 0,
                test_reads,
                0,
            ),
        ]
    )
    if not contracts["status"].eq("pass").all():
        raise ValueError("LightGBM aggregation contracts failed")
    readiness = pd.DataFrame(
        [
            {
                "lightgbm_split_count_complete": 3,
                "lightgbm_development_complete": True,
                "lightgbm_model_research_complete": False,
                "pre_test_freeze_ready": True,
                "single_test_release_complete": False,
                "research_model_experiment_started": True,
                "model_training_started": True,
                "test_read_count_before_freeze": test_reads,
                "production_model_selected": False,
                "authoritative_execution": False,
                "unbiased_final_estimate": False,
            }
        ]
    )
    parent_receipts = pd.DataFrame(
        [
            {
                "parent_role": role,
                "manifest_path": path.as_posix(),
                "stage_id": manifest["stage_id"],
                "artifact_id": manifest["artifact_id"],
                "artifact_status": manifest["artifact_status"],
                "lineage_status": manifest["lineage_status"],
                "direct_parent": True,
            }
            for role, path, manifest in parents
        ]
    )
    resolved_config = {
        **config,
        "executed_command": command,
        "executed_scope": "aggregate_3_split_lightgbm",
        "input_artifact_ids": parent_receipts[
            "artifact_id"
        ].tolist(),
        "output_dir": output_dir.as_posix(),
    }
    with StageOutputPublisher(output_dir, OUTPUTS) as publisher:
        for filename, frame in frames.items():
            frame.to_csv(publisher.path(filename), index=False)
        publisher.path("selected_hyperparameters.json").write_text(
            json.dumps(
                selected,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        access.to_csv(
            publisher.path("access_audit.csv"), index=False
        )
        contracts.to_csv(
            publisher.path("contract_status.csv"), index=False
        )
        readiness.to_csv(
            publisher.path("readiness_summary.csv"), index=False
        )
        parent_receipts.to_csv(
            publisher.path("parent_receipts.csv"), index=False
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(
                resolved_config,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )
        for filename, payload in freezes.items():
            publisher.path(
                f"pre_test_freezes/{filename}"
            ).write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        publisher.path("run_report.md").write_text(
            "# Research LightGBM V1 Development Aggregate\n\n"
            "- LightGBM development: 3/3 splits complete.\n"
            "- Frozen candidates: 16 per split, 48 total.\n"
            "- Final train+validation models: 3.\n"
            "- Immutable base pre-test freezes: 3.\n"
            f"- Test payload reads before freeze: {test_reads}.\n"
            "- Test release has not started.\n",
            encoding="utf-8",
        )
        output_files = [
            publisher.path(name)
            for name in OUTPUTS
            if name != "artifact_manifest.json"
        ]
        protocol_manifest = load_artifact_manifest(
            protocol_manifest_path
        )
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id=STAGE_ID,
            config=resolved_config,
            output_dir=publisher.staging_dir,
            output_files=output_files,
            code_state=code_state,
            input_manifest_paths=[
                protocol_manifest_path,
                *(path for _, path, _ in parents),
            ],
            universe_artifact_id=protocol_manifest.get(
                "universe_artifact_id"
            ),
            split_manifest_id=protocol_manifest.get(
                "split_manifest_id"
            ),
            factor_catalog_id=protocol_manifest.get(
                "factor_catalog_id"
            ),
            factor_frame_id=protocol_manifest.get(
                "factor_frame_id"
            ),
            contract_paths=[
                publisher.path("contract_status.csv")
            ],
        )
        publisher.publish()
    return {
        "output_dir": output_dir.as_posix(),
        "model_count": len(models),
        "freeze_count": len(freezes),
        "test_read_count": test_reads,
        "aggregate_sha256": canonical_hash(
            {
                "selected": selected,
                "model_hashes": sorted(
                    models["model_binary_sha256"].astype(str)
                ),
            }
        ),
    }
