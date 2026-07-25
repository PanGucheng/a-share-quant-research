from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

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
from .inputs import load_fold_dates
from .lightgbm_models import _contract
from .protocol import PROJECT_ROOT, parent_paths, resolve


STAGE_ID = "research_lightgbm_test_release_freeze_v1"
FREEZE_NAMES = tuple(
    f"split_{index:03d}_lightgbm.json" for index in range(1, 4)
)
OUTPUTS = (
    "artifact_manifest.json",
    "resolved_config.json",
    "parent_receipts.csv",
    "release_freeze_index.csv",
    "access_audit.csv",
    "contract_status.csv",
    "readiness_summary.csv",
    "run_report.md",
    *(f"release_freezes/{name}" for name in FREEZE_NAMES),
)


def publish_lightgbm_test_release_freezes(
    config: dict[str, Any],
    *,
    output_dir: Path,
    command: str,
) -> dict[str, Any]:
    protocol_manifest_path = resolve(config["protocol_manifest"])
    assert_research_model_entry_artifact(
        protocol_manifest_path,
        experiment_class=str(config["experiment_class"]),
        operation="prediction",
    )
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError(
            "LightGBM release freeze requires clean committed code"
        )
    development_path = resolve(
        "outputs/research_lightgbm_v1/development/"
        "artifact_manifest.json"
    )
    development = load_artifact_manifest(development_path)
    issues = validate_manifest_outputs(
        development, development_path.parent
    )
    readiness = pd.read_csv(
        development_path.parent / "readiness_summary.csv"
    )
    if (
        development.get("artifact_status") != "pass"
        or development.get("lineage_status") != "complete"
        or issues
        or len(readiness) != 1
        or not bool(
            readiness.iloc[0]["lightgbm_development_complete"]
        )
    ):
        raise ValueError(
            "LightGBM development is not complete/pass"
        )
    protocol_config = yaml.safe_load(
        resolve(config["protocol_config"]).read_text(encoding="utf-8")
    )
    date_manifest_path = parent_paths(protocol_config).date_manifest
    date_manifest = load_artifact_manifest(date_manifest_path)
    if (
        date_manifest.get("stage_id") != "date_split_semantics_v1"
        or validate_manifest_outputs(
            date_manifest, date_manifest_path.parent
        )
    ):
        raise ValueError("LightGBM date authority is invalid")
    assignments_path = (
        parent_paths(protocol_config).selection_date_assignments
    )
    assignments_sha = file_sha256(assignments_path)
    freezes: dict[str, dict[str, Any]] = {}
    index_rows: list[dict[str, Any]] = []
    for filename in FREEZE_NAMES:
        base_path = (
            development_path.parent
            / "pre_test_freezes"
            / filename
        )
        base = json.loads(base_path.read_text(encoding="utf-8"))
        validate_pre_test_freeze(base)
        test_dates = load_fold_dates(
            assignments_path,
            outer_split_id=str(base["outer_split_id"]),
            fold="test",
        )
        payload = {
            **base,
            "release_freeze_schema_version": 1,
            "base_freeze_sha256": file_sha256(base_path),
            "development_artifact_id": development["artifact_id"],
            "date_authority_artifact_id": date_manifest[
                "artifact_id"
            ],
            "date_assignment_sha256": assignments_sha,
            "test_dates_sha256": canonical_hash(
                [value.date().isoformat() for value in test_dates]
            ),
            "test_date_count": len(test_dates),
            "test_start_date": (
                test_dates.min().date().isoformat()
            ),
            "test_end_date": test_dates.max().date().isoformat(),
            "release_freeze_code_commit_sha": code_state.commit_sha,
            "test_payload_read_count_at_freeze": 0,
        }
        payload["freeze_id"] = (
            "lightgbm-test-release-freeze:"
            + canonical_hash(payload)
        )
        validate_pre_test_freeze(payload)
        freezes[filename] = payload
        index_rows.append(
            {
                "outer_split_id": payload["outer_split_id"],
                "method": payload["method"],
                "freeze_path": f"release_freezes/{filename}",
                "freeze_id": payload["freeze_id"],
                "base_freeze_sha256": payload[
                    "base_freeze_sha256"
                ],
                "test_dates_sha256": payload["test_dates_sha256"],
                "test_date_count": payload["test_date_count"],
                "model_binary_sha256": payload[
                    "model_binary_sha256"
                ],
                "status": "pass",
            }
        )
    index = pd.DataFrame(index_rows).sort_values(
        ["outer_split_id"], kind="stable"
    )
    expected_keys = {
        (f"split_{value:03d}", "lightgbm")
        for value in range(1, 4)
    }
    observed_keys = set(
        zip(
            index["outer_split_id"].astype(str),
            index["method"].astype(str),
        )
    )
    contracts = pd.DataFrame(
        [
            _contract(
                "lightgbm_development_artifact_valid",
                True,
                development["artifact_id"],
                "passing complete development artifact",
            ),
            _contract(
                "date_split_semantics_authority_consumed",
                date_manifest["stage_id"]
                == "date_split_semantics_v1",
                date_manifest["stage_id"],
                "date_split_semantics_v1",
            ),
            _contract(
                "release_freeze_split_coverage_exact",
                observed_keys == expected_keys and len(index) == 3,
                sorted(observed_keys),
                sorted(expected_keys),
            ),
            _contract(
                "test_dates_explicitly_frozen",
                index["test_dates_sha256"].nunique() == 3
                and (index["test_date_count"] > 0).all(),
                index[
                    ["outer_split_id", "test_date_count"]
                ].to_dict("records"),
                "three non-empty exact test date sets",
            ),
            _contract(
                "test_read_count_before_release_zero",
                True,
                0,
                0,
            ),
        ]
    )
    if not contracts["status"].eq("pass").all():
        raise ValueError(
            "LightGBM release freeze contracts failed"
        )
    stage_readiness = pd.DataFrame(
        [
            {
                "lightgbm_development_complete": True,
                "release_freeze_ready": True,
                "single_test_release_complete": False,
                "test_payload_read_count_at_freeze": 0,
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
                "stage_id": manifest["stage_id"],
                "artifact_id": manifest["artifact_id"],
                "manifest_path": path.as_posix(),
                "artifact_status": manifest["artifact_status"],
                "lineage_status": manifest["lineage_status"],
                "direct_parent": True,
            }
            for role, path, manifest in (
                (
                    "lightgbm_development",
                    development_path,
                    development,
                ),
                (
                    "date_split_authority",
                    date_manifest_path,
                    date_manifest,
                ),
            )
        ]
    )
    resolved_config = {
        **config,
        "executed_command": command,
        "executed_scope": (
            "freeze_exact_test_dates_for_3_lightgbm_models"
        ),
        "development_artifact_id": development["artifact_id"],
        "date_authority_artifact_id": date_manifest[
            "artifact_id"
        ],
        "date_assignment_sha256": assignments_sha,
        "output_dir": output_dir.as_posix(),
    }
    with StageOutputPublisher(output_dir, OUTPUTS) as publisher:
        for filename, payload in freezes.items():
            publisher.path(
                f"release_freezes/{filename}"
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
        index.to_csv(
            publisher.path("release_freeze_index.csv"), index=False
        )
        pd.DataFrame(
            [
                {"input_kind": kind, "fold": fold, "read_count": 0}
                for kind in ("feature", "label")
                for fold in ("train", "validation", "test")
            ]
        ).to_csv(publisher.path("access_audit.csv"), index=False)
        contracts.to_csv(
            publisher.path("contract_status.csv"), index=False
        )
        stage_readiness.to_csv(
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
        publisher.path("run_report.md").write_text(
            "# Research LightGBM V1 Test Release Freeze\n\n"
            "- Three final models are bound to exact authoritative "
            "test dates.\n"
            f"- Date assignment SHA: `{assignments_sha}`.\n"
            "- Test payload reads at freeze: 0.\n"
            "- Historical test is already observed and remains "
            "non-authoritative.\n",
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
                development_path,
                date_manifest_path,
            ],
            universe_artifact_id=development.get(
                "universe_artifact_id"
            ),
            split_manifest_id=development.get("split_manifest_id"),
            factor_catalog_id=development.get(
                "factor_catalog_id"
            ),
            factor_frame_id=development.get("factor_frame_id"),
            contract_paths=[
                publisher.path("contract_status.csv")
            ],
        )
        publisher.publish()
    return {
        "output_dir": output_dir.as_posix(),
        "freeze_count": len(freezes),
        "test_read_count": 0,
    }
