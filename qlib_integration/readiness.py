from __future__ import annotations

from pathlib import Path
from typing import Mapping

import pandas as pd
import yaml

from research_validation.lineage import LineageIssue, load_artifact_manifest, validate_manifest_outputs


def contract_ready(path: Path, severities: set[str]) -> bool:
    if not path.is_file():
        return False
    frame = pd.read_csv(path)
    return frame.loc[frame["severity"].isin(severities) & frame["status"].isin(["blocked", "fail"])].empty


def validate_execution_evidence(
    project_root: Path,
    evidence: Mapping[str, Mapping[str, str]],
) -> tuple[dict[str, dict[str, object]], list[LineageIssue]]:
    loaded: dict[str, dict[str, object]] = {}
    issues: list[LineageIssue] = []
    artifact_ids: dict[str, str] = {}
    for name, spec in evidence.items():
        manifest_path = project_root / spec["manifest"]
        config_path = project_root / spec["config"]
        if not manifest_path.is_file():
            issues.append(LineageIssue("manifest_missing", "", manifest_path.as_posix(), name))
            continue
        manifest = load_artifact_manifest(manifest_path)
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        output_dir = project_root / str(config["output_dir"])
        issues.extend(validate_manifest_outputs(manifest, output_dir, config=config))
        if bool(manifest["code_dirty"]):
            issues.append(LineageIssue("clean_code", str(manifest["artifact_id"]), "evidence was produced from a dirty tree", str(manifest["stage_id"])))
        if manifest["artifact_status"] != "pass":
            issues.append(LineageIssue("artifact_status", str(manifest["artifact_id"]), str(manifest["blocked_reason"]), str(manifest["stage_id"])))
        loaded[name] = manifest
        artifact_ids[name] = str(manifest["artifact_id"])

    expected_edges = {
        "synthetic": ["environment"],
        "reconciliation": ["synthetic"],
        "reference": ["environment"],
    }
    for child_name, parent_names in expected_edges.items():
        child = loaded.get(child_name)
        if child is None:
            continue
        inputs = set(map(str, child["input_artifact_ids"]))
        for parent_name in parent_names:
            parent_id = artifact_ids.get(parent_name)
            if parent_id is None or parent_id not in inputs:
                issues.append(LineageIssue("stale_upstream_artifact", str(child["artifact_id"]), f"does not reference current {parent_name}: {parent_id}", str(child["stage_id"])))
    return loaded, issues
