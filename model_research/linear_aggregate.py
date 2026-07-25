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
from .protocol import PROJECT_ROOT, resolve


STAGE_ID = "research_linear_models_v1"
PARENT_SPECS = (
    (
        "ridge_all",
        "outputs/research_linear_models_v1/ridge_all/artifact_manifest.json",
    ),
    (
        "elastic_split_001",
        "outputs/research_linear_models_v1/elastic_split_001/artifact_manifest.json",
    ),
    (
        "elastic_remaining",
        "outputs/research_linear_models_v1/elastic_remaining/artifact_manifest.json",
    ),
)
FRAME_FILES = (
    "candidate_manifest.csv",
    "validation_metrics.csv",
    "coefficient_summary.csv",
    "preprocessing_receipt.csv",
    "model_receipt.csv",
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
    "pre_test_freezes/split_001_ridge.json",
    "pre_test_freezes/split_002_ridge.json",
    "pre_test_freezes/split_003_ridge.json",
    "pre_test_freezes/split_001_elastic_net.json",
    "pre_test_freezes/split_002_elastic_net.json",
    "pre_test_freezes/split_003_elastic_net.json",
)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _contract(
    name: str, passed: bool, observed: object, expected: object
) -> dict[str, object]:
    return {
        "check_name": name,
        "status": "pass" if passed else "blocked",
        "severity": "critical",
        "observed": json.dumps(observed, ensure_ascii=False, default=str),
        "expected": json.dumps(expected, ensure_ascii=False, default=str),
        "reason": "" if passed else f"{name} failed",
    }


def aggregate_linear_development(
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
        raise ValueError("linear aggregation requires a clean committed worktree")
    parent_entries: list[tuple[str, Path, dict[str, Any]]] = []
    for role, value in PARENT_SPECS:
        path = resolve(value)
        manifest = load_artifact_manifest(path)
        if manifest.get("stage_id") != STAGE_ID:
            raise ValueError(f"{role} stage mismatch")
        if manifest.get("artifact_status") != "pass":
            raise ValueError(f"{role} artifact is not pass")
        issues = validate_manifest_outputs(manifest, path.parent)
        if issues:
            raise ValueError(
                f"{role} output hash failures: "
                + " | ".join(item.reason for item in issues)
            )
        parent_entries.append((role, path, manifest))

    frames: dict[str, pd.DataFrame] = {}
    for filename in FRAME_FILES:
        values: list[pd.DataFrame] = []
        for role, path, _ in parent_entries:
            frame = pd.read_csv(path.parent / filename)
            frame.insert(0, "source_evidence", role)
            values.append(frame)
        frames[filename] = pd.concat(values, ignore_index=True)
    selected: dict[str, Any] = {}
    for _, path, _ in parent_entries:
        payload = json.loads(
            (path.parent / "selected_hyperparameters.json").read_text(
                encoding="utf-8"
            )
        )
        overlap = set(selected) & set(payload)
        if overlap:
            raise ValueError(f"duplicate selected parameter keys: {overlap}")
        selected.update(payload)

    freezes: dict[str, dict[str, Any]] = {}
    for _, path, _ in parent_entries:
        for freeze_path in sorted(
            (path.parent / "pre_test_freezes").glob("*.json")
        ):
            if freeze_path.name in freezes:
                raise ValueError(f"duplicate freeze: {freeze_path.name}")
            payload = json.loads(freeze_path.read_text(encoding="utf-8"))
            validate_pre_test_freeze(payload)
            freezes[freeze_path.name] = payload

    models = frames["model_receipt.csv"]
    preprocessing = frames["preprocessing_receipt.csv"]
    runtime_model_hashes_valid = all(
        Path(str(row.runtime_path)).is_file()
        and file_sha256(Path(str(row.runtime_path)))
        == str(row.model_binary_sha256)
        for row in models.itertuples(index=False)
    )
    runtime_preprocessing_hashes_valid = all(
        Path(str(row.runtime_path)).is_file()
        and file_sha256(Path(str(row.runtime_path)))
        == str(row.preprocessing_sha256)
        for row in preprocessing.itertuples(index=False)
    )
    expected_keys = {
        f"split_{index:03d}:{method}"
        for index in range(1, 4)
        for method in ("ridge", "elastic_net")
    }
    observed_keys = {
        f"{row.outer_split_id}:{row.method}"
        for row in models.itertuples(index=False)
    }
    candidate_counts = (
        frames["candidate_manifest.csv"]
        .groupby(["outer_split_id", "method"])
        .size()
        .to_dict()
    )
    candidate_counts_valid = all(
        int(candidate_counts.get((f"split_{index:03d}", method), 0))
        == (5 if method == "ridge" else 15)
        for index in range(1, 4)
        for method in ("ridge", "elastic_net")
    )
    access_values: list[pd.DataFrame] = []
    for role, path, _ in parent_entries:
        value = pd.read_csv(path.parent / "access_audit.csv")
        value["source_evidence"] = role
        access_values.append(value)
    access_detail = pd.concat(access_values, ignore_index=True)
    access = (
        access_detail.groupby(["input_kind", "fold"], as_index=False)[
            "read_count"
        ]
        .sum()
        .sort_values(["input_kind", "fold"], kind="stable")
    )
    test_reads = int(
        access.loc[access["fold"].astype(str).eq("test"), "read_count"].sum()
    )
    mutations_valid = (
        not frames["mutation_results.csv"].empty
        and frames["mutation_results.csv"]["status"].eq("pass").all()
    )
    freezes_valid = set(freezes) == {
        key.replace(":", "_") + ".json" for key in expected_keys
    }
    freeze_model_hashes_valid = all(
        payload["model_binary_sha256"]
        == str(
            models.loc[
                models["outer_split_id"].eq(payload["outer_split_id"])
                & models["method"].eq(payload["method"]),
                "model_binary_sha256",
            ].iloc[0]
        )
        for payload in freezes.values()
    )
    contracts = pd.DataFrame(
        [
            _contract(
                "linear_split_method_coverage_exact",
                observed_keys == expected_keys,
                sorted(observed_keys),
                sorted(expected_keys),
            ),
            _contract(
                "candidate_grid_exact",
                candidate_counts_valid,
                {str(key): value for key, value in candidate_counts.items()},
                "5 Ridge and 15 Elastic Net candidates per split",
            ),
            _contract(
                "validation_mutation_invariance_pass",
                mutations_valid,
                frames["mutation_results.csv"]["status"].tolist(),
                "all pass",
            ),
            _contract(
                "model_binary_hash_valid",
                runtime_model_hashes_valid,
                runtime_model_hashes_valid,
                True,
            ),
            _contract(
                "fitted_preprocessing_hash_valid",
                runtime_preprocessing_hashes_valid,
                runtime_preprocessing_hashes_valid,
                True,
            ),
            _contract(
                "pre_test_freeze_valid",
                freezes_valid and freeze_model_hashes_valid,
                {
                    "freeze_count": len(freezes),
                    "model_hashes_valid": freeze_model_hashes_valid,
                },
                {"freeze_count": 6, "model_hashes_valid": True},
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
        raise ValueError(
            "linear aggregation contracts failed: "
            + ",".join(
                contracts.loc[
                    ~contracts["status"].eq("pass"), "check_name"
                ].astype(str)
            )
        )
    readiness = pd.DataFrame(
        [
            {
                "ridge_split_count_complete": 3,
                "elastic_net_split_count_complete": 3,
                "linear_model_development_complete": True,
                "linear_model_research_complete": False,
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
    protocol_manifest = load_artifact_manifest(protocol_manifest_path)
    parent_receipts = pd.DataFrame(
        [
            {
                "parent_role": role,
                "stage_id": manifest["stage_id"],
                "artifact_id": manifest["artifact_id"],
                "manifest_path": path.as_posix(),
                "artifact_status": manifest["artifact_status"],
                "lineage_status": manifest["lineage_status"],
                "direct_parent": True,
            }
            for role, path, manifest in parent_entries
        ]
    )
    resolved_config = {
        **config,
        "executed_command": command,
        "executed_scope": "aggregate_3_split_ridge_and_elastic_net",
        "input_artifact_ids": parent_receipts["artifact_id"].tolist(),
        "output_dir": output_dir.as_posix(),
    }
    with StageOutputPublisher(output_dir, OUTPUTS) as publisher:
        for filename, frame in frames.items():
            frame.to_csv(publisher.path(filename), index=False)
        _write_json(
            publisher.path("selected_hyperparameters.json"), selected
        )
        access.to_csv(publisher.path("access_audit.csv"), index=False)
        contracts.to_csv(publisher.path("contract_status.csv"), index=False)
        readiness.to_csv(
            publisher.path("readiness_summary.csv"), index=False
        )
        parent_receipts.to_csv(
            publisher.path("parent_receipts.csv"), index=False
        )
        _write_json(publisher.path("resolved_config.json"), resolved_config)
        for filename, payload in freezes.items():
            _write_json(
                publisher.path(f"pre_test_freezes/{filename}"), payload
            )
        publisher.path("run_report.md").write_text(
            "# Research Linear Models V1 Development Aggregate\n\n"
            "- Ridge development: 3/3 splits complete.\n"
            "- Elastic Net development: 3/3 splits complete.\n"
            f"- Candidate rows: {len(frames['candidate_manifest.csv'])}.\n"
            "- Final train+validation models: 6.\n"
            "- Immutable pre-test freezes: 6.\n"
            f"- Test payload reads before freeze: {test_reads}.\n"
            "- Test release has not started.\n",
            encoding="utf-8",
        )
        output_files = [
            publisher.path(name)
            for name in OUTPUTS
            if name != "artifact_manifest.json"
        ]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id=STAGE_ID,
            config=resolved_config,
            output_dir=publisher.staging_dir,
            output_files=output_files,
            code_state=code_state,
            input_manifest_paths=[
                protocol_manifest_path,
                *(path for _, path, _ in parent_entries),
            ],
            universe_artifact_id=protocol_manifest.get(
                "universe_artifact_id"
            ),
            split_manifest_id=protocol_manifest.get("split_manifest_id"),
            factor_catalog_id=protocol_manifest.get("factor_catalog_id"),
            factor_frame_id=protocol_manifest.get("factor_frame_id"),
            contract_paths=[publisher.path("contract_status.csv")],
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

