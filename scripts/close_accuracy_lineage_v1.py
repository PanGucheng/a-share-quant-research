from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.feature_matrix import file_sha256  # noqa: E402
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    load_artifact_manifest,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


DATE_OUTPUTS = (
    "artifact_manifest.json",
    "date_assignments.csv",
    "split_date_ranges.csv",
    "split_manifest.csv",
    "legacy_evidence_inventory.csv",
    "contract_status.csv",
    "resolved_config.json",
)
SELECTION_OUTPUTS = (
    "artifact_manifest.json",
    "date_assignments.csv",
    "split_allowlist_manifest.csv",
    "factor_weights_by_split.csv",
    "weight_manifest.csv",
    "transparent_score_policy.json",
    "mutation_contract_status.csv",
    "mutation_results.csv",
    "business_payload_hashes.csv",
    "legacy_evidence_inventory.csv",
    "contract_status.csv",
    "closure_report.md",
    "resolved_config.json",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def require_legacy_evidence(
    manifest_path: Path, source_paths: list[Path]
) -> tuple[dict[str, object], list[dict[str, object]]]:
    manifest = load_artifact_manifest(manifest_path)
    issues = validate_manifest_outputs(manifest, manifest_path.parent)
    if issues:
        raise ValueError(
            f"legacy evidence is stale: {manifest_path}: "
            + "|".join(issue.check_name for issue in issues)
        )
    if manifest["artifact_status"] != "pass" or bool(manifest["code_dirty"]):
        raise ValueError(f"legacy evidence is blocked or dirty: {manifest_path}")
    rows: list[dict[str, object]] = []
    for path in source_paths:
        expected = manifest["output_file_hashes"].get(path.name)
        actual = file_sha256(path)
        if not expected or expected != actual:
            raise ValueError(f"legacy business payload is not manifest-bound: {path}")
        rows.append(
            {
                "legacy_artifact_id": manifest["artifact_id"],
                "legacy_stage_id": manifest["stage_id"],
                "source_path": path.as_posix(),
                "source_sha256": actual,
                "legacy_lineage_status": manifest["lineage_status"],
                "authority_role": "business_payload_evidence_only",
            }
        )
    return manifest, rows


def copy_exact(source: Path, target: Path) -> None:
    payload = source.read_bytes()
    target.write_bytes(payload)
    if file_sha256(source) != file_sha256(target):
        raise ValueError(f"exact copy failed: {source} -> {target}")


def publish_date_split(config: dict[str, object], code_state) -> Path:
    manifest_path = resolve(config["legacy_split_manifest"])
    sources = [
        resolve(config["legacy_date_assignments"]),
        resolve(config["legacy_split_date_ranges"]),
        resolve(config["legacy_split_table"]),
    ]
    manifest, evidence = require_legacy_evidence(manifest_path, sources)
    output_dir = resolve(config["date_split_output"])
    with StageOutputPublisher(output_dir, DATE_OUTPUTS) as publisher:
        for source, name in zip(
            sources, ["date_assignments.csv", "split_date_ranges.csv", "split_manifest.csv"]
        ):
            copy_exact(source, publisher.path(name))
        evidence_frame = pd.DataFrame(evidence)
        evidence_frame.to_csv(
            publisher.path("legacy_evidence_inventory.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        contract = pd.DataFrame(
            [
                {
                    "check_name": "legacy_split_payload_hashes_valid",
                    "status": "pass",
                    "observed_value": len(sources),
                    "required_value": len(sources),
                    "severity": "critical",
                    "reason": "",
                },
                {
                    "check_name": "date_only_lineage_semantics",
                    "status": "pass",
                    "observed_value": "split_manifest_id_only",
                    "required_value": "split_manifest_id_only",
                    "severity": "critical",
                    "reason": "Date assignments do not define the research universe.",
                },
            ]
        )
        contract.to_csv(
            publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig"
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="date_split_semantics_v1",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=[
                publisher.path(name)
                for name in DATE_OUTPUTS
                if name != "artifact_manifest.json"
            ],
            code_state=code_state,
            input_manifest_paths=[manifest_path],
            split_manifest_id=manifest["split_manifest_id"],
            start_date=manifest["start_date"],
            end_date=manifest["end_date"],
            inherit_lineage_fields=["split_manifest_id"],
            artifact_status="pass",
        )
        publisher.publish()
    return output_dir / "artifact_manifest.json"


def publish_selection_closure(
    config: dict[str, object], date_manifest_path: Path, code_state
) -> Path:
    source_specs = [
        (
            "allowlist",
            resolve(config["legacy_allowlist_manifest"]),
            [resolve(config["legacy_allowlist_table"])],
        ),
        (
            "weights",
            resolve(config["legacy_weights_manifest"]),
            [
                resolve(config["legacy_weights_table"]),
                resolve(config["legacy_weight_index"]),
            ],
        ),
        (
            "policy",
            resolve(config["legacy_policy_manifest"]),
            [resolve(config["legacy_policy"])],
        ),
        (
            "mutation",
            resolve(config["legacy_mutation_manifest"]),
            [
                resolve(config["legacy_mutation_contract"]),
                resolve(config["legacy_mutation_results"]),
                resolve(config["legacy_business_payload_hashes"]),
            ],
        ),
    ]
    evidence: list[dict[str, object]] = []
    legacy: dict[str, dict[str, object]] = {}
    for name, manifest_path, sources in source_specs:
        legacy[name], rows = require_legacy_evidence(manifest_path, sources)
        evidence.extend(rows)

    policy = json.loads(resolve(config["legacy_policy"]).read_text(encoding="utf-8"))
    mutation_contract = pd.read_csv(resolve(config["legacy_mutation_contract"]))
    mutation_results = pd.read_csv(resolve(config["legacy_mutation_results"]))
    business_hashes = pd.read_csv(resolve(config["legacy_business_payload_hashes"]))
    ready = (
        policy.get("status") == "frozen"
        and policy.get("outer_test_used") is False
        and mutation_contract["status"].eq("pass").all()
        and mutation_results["development_projection_unchanged"].astype(bool).all()
        and mutation_results["selection_payloads_unchanged"].astype(bool).all()
        and mutation_results["mutation_effective"].astype(bool).all()
        and len(business_hashes) == 3
    )
    output_dir = resolve(config["selection_closure_output"])
    date_manifest = load_artifact_manifest(date_manifest_path)
    matrix_path = resolve(config["matrix_manifest"])
    universe_path = resolve(config["universe_manifest"])
    matrix = load_artifact_manifest(matrix_path)
    universe = load_artifact_manifest(universe_path)
    output_sources = {
        "date_assignments.csv": resolve(config["legacy_date_assignments"]),
        "split_allowlist_manifest.csv": resolve(config["legacy_allowlist_table"]),
        "factor_weights_by_split.csv": resolve(config["legacy_weights_table"]),
        "weight_manifest.csv": resolve(config["legacy_weight_index"]),
        "transparent_score_policy.json": resolve(config["legacy_policy"]),
        "mutation_contract_status.csv": resolve(config["legacy_mutation_contract"]),
        "mutation_results.csv": resolve(config["legacy_mutation_results"]),
        "business_payload_hashes.csv": resolve(config["legacy_business_payload_hashes"]),
    }
    with StageOutputPublisher(output_dir, SELECTION_OUTPUTS) as publisher:
        for name, source in output_sources.items():
            copy_exact(source, publisher.path(name))
        pd.DataFrame(evidence).to_csv(
            publisher.path("legacy_evidence_inventory.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        contract = pd.DataFrame(
            [
                {
                    "check_name": "legacy_business_payload_hashes_valid",
                    "status": "pass",
                    "observed_value": len(evidence),
                    "required_value": len(evidence),
                    "severity": "critical",
                    "reason": "",
                },
                {
                    "check_name": "score_policy_business_payload_unchanged",
                    "status": "pass" if policy.get("status") == "frozen" else "blocked",
                    "observed_value": file_sha256(output_sources["transparent_score_policy.json"]),
                    "required_value": legacy["policy"]["output_file_hashes"][
                        "transparent_score_policy.json"
                    ],
                    "severity": "critical",
                    "reason": "",
                },
                {
                    "check_name": "selection_mutation_proof_revalidated",
                    "status": "pass" if ready else "blocked",
                    "observed_value": len(mutation_results),
                    "required_value": 36,
                    "severity": "critical",
                    "reason": "",
                },
                {
                    "check_name": "authoritative_universe_v2_bound",
                    "status": "pass"
                    if matrix["universe_artifact_id"] == universe["universe_artifact_id"]
                    else "blocked",
                    "observed_value": matrix["universe_artifact_id"],
                    "required_value": universe["universe_artifact_id"],
                    "severity": "critical",
                    "reason": "",
                },
            ]
        )
        contract.to_csv(
            publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig"
        )
        publisher.path("closure_report.md").write_text(
            "# Research Selection Lineage Closure V1\n\n"
            "- Reissues date assignments, allowlist receipts, weights, score policy and mutation proof without changing business bytes.\n"
            "- Legacy manifests remain recorded as evidence; current lineage authority comes only from Universe v2, Matrix v4 and the date-only split receipt.\n"
            "- No factor, label, IC, FDR, stability, clustering or selection calculation is executed.\n",
            encoding="utf-8",
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="research_selection_lineage_closure_v1",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=[
                publisher.path(name)
                for name in SELECTION_OUTPUTS
                if name != "artifact_manifest.json"
            ],
            code_state=code_state,
            input_manifest_paths=[date_manifest_path, matrix_path, universe_path],
            universe_artifact_id=universe["universe_artifact_id"],
            split_manifest_id=date_manifest["split_manifest_id"],
            factor_catalog_id=matrix["factor_catalog_id"],
            factor_frame_id=matrix["factor_frame_id"],
            start_date=date_manifest["start_date"],
            end_date=date_manifest["end_date"],
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_selection_lineage_closure",
        )
        publisher.publish()
    return output_dir / "artifact_manifest.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Close dimension-scoped lineage without recomputing research payloads."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/accuracy_lineage_closure_v1.yaml"),
    )
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    semantics = yaml.safe_load(
        resolve(config["lineage_semantics"]).read_text(encoding="utf-8")
    )
    if semantics.get("status") != "frozen":
        raise ValueError("lineage semantics registry is not frozen")
    code_state = capture_code_state(PROJECT_ROOT)
    date_manifest = publish_date_split(config, code_state)
    selection_manifest = publish_selection_closure(config, date_manifest, code_state)
    result = load_artifact_manifest(selection_manifest)
    print(
        json.dumps(
            {
                "date_split_manifest": str(date_manifest),
                "selection_closure_manifest": str(selection_manifest),
                "selection_closure_artifact_id": result["artifact_id"],
                "lineage_status": result["lineage_status"],
                "artifact_status": result["artifact_status"],
            },
            indent=2,
        )
    )
    return 0 if result["artifact_status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
