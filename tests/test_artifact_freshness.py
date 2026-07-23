from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from research_validation.lineage import (
    CodeState,
    build_artifact_manifest,
    capture_code_state,
    critical_contract_failures,
    direct_parent_gate_failures,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.profiles import Profile, ProfileType


def test_output_hash_mismatch_is_blocking(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    output = runtime / "scores.parquet"
    output.write_bytes(b"first")
    config = {"value": 1}
    manifest = build_artifact_manifest(
        stage_id="score", profile=Profile("local_reference", ProfileType.REFERENCE), config=config,
        output_files=[output], output_dir=tmp_path, code_state=CodeState("abc", False, ""),
        created_at=datetime(2026, 7, 13, tzinfo=timezone.utc), run_id="run-score",
    )
    assert manifest["output_file_hashes"].keys() == {"runtime/scores.parquet"}
    assert validate_manifest_outputs(manifest, tmp_path, config=config) == []
    output.write_bytes(b"changed")
    assert "output_hash_mismatch" in {item.check_name for item in validate_manifest_outputs(manifest, tmp_path, config=config)}


def test_v1_manifest_cannot_prove_freshness(tmp_path: Path) -> None:
    output = tmp_path / "data.csv"
    output.write_text("a\n1\n", encoding="utf-8")
    manifest = build_artifact_manifest(
        stage_id="legacy", profile=Profile("local_reference", ProfileType.REFERENCE), config={},
        output_files=[output], output_dir=tmp_path, code_state=CodeState("abc", False, ""), run_id="legacy",
    )
    manifest["schema_version"] = 1
    for field in ("artifact_status", "blocked_reason", "research_run_family_id", "producer_run_id"):
        manifest.pop(field)
    issues = validate_manifest_outputs(manifest, tmp_path)
    assert {item.check_name for item in issues} == {"manifest_freshness_schema"}


def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)


def test_code_dirty_includes_untracked_source_but_excludes_outputs(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    tracked = tmp_path / "README.md"
    tracked.write_text("tracked", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "init")
    output = tmp_path / "outputs" / "run.csv"
    output.parent.mkdir()
    output.write_text("runtime", encoding="utf-8")
    assert not capture_code_state(tmp_path).dirty
    (tmp_path / "new_module.py").write_text("VALUE = 1\n", encoding="utf-8")
    assert capture_code_state(tmp_path).dirty


def test_critical_contract_failure_is_fail_closed(tmp_path: Path) -> None:
    contract = tmp_path / "contract_status.csv"
    contract.write_text(
        "check_name,status,severity\nlot_rule_resolved,blocked,critical\n",
        encoding="utf-8",
    )
    output = tmp_path / "result.csv"
    output.write_text("value\n1\n", encoding="utf-8")
    manifest = write_stage_artifact_manifest(
        project_root=tmp_path,
        stage_id="child",
        config={
            "profile_name": "full_research",
            "profile_type": "full_research",
            "research_run_family_id": "fixture",
        },
        output_dir=tmp_path,
        output_files=[contract, output],
        code_state=CodeState("abc", False, ""),
        artifact_status="pass",
    )
    assert manifest["artifact_status"] == "blocked"
    assert "critical_contract" in manifest["blocked_reason"]
    assert critical_contract_failures([contract])


def test_capability_contract_does_not_block_operational_artifact(tmp_path: Path) -> None:
    contract = tmp_path / "contract_status.csv"
    contract.write_text(
        "check_name,status,severity\nhistorical_state,blocked,capability\n",
        encoding="utf-8",
    )
    manifest = write_stage_artifact_manifest(
        project_root=tmp_path,
        stage_id="child",
        config={
            "profile_name": "full_research",
            "profile_type": "full_research",
            "research_run_family_id": "fixture",
        },
        output_dir=tmp_path,
        output_files=[contract],
        code_state=CodeState("abc", False, ""),
        artifact_status="pass",
    )
    assert manifest["artifact_status"] == "pass"


def test_inconsistent_or_dirty_parent_blocks_complete_child(tmp_path: Path) -> None:
    parent = build_artifact_manifest(
        stage_id="parent",
        profile=Profile("full_research", ProfileType.FULL_RESEARCH),
        config={"research_run_family_id": "fixture"},
        output_files=[],
        code_state=CodeState("abc", True, "dirty"),
        lineage_status="inconsistent",
        artifact_status="pass",
        run_id="parent",
    )
    parent_path = tmp_path / "parent.json"
    from research_validation.lineage import write_artifact_manifest

    write_artifact_manifest(parent_path, parent)
    manifest = write_stage_artifact_manifest(
        project_root=tmp_path,
        stage_id="child",
        config={
            "profile_name": "full_research",
            "profile_type": "full_research",
            "research_run_family_id": "fixture",
        },
        output_dir=tmp_path,
        output_files=[],
        input_manifest_paths=[parent_path],
        code_state=CodeState("def", False, ""),
        lineage_status="complete",
        artifact_status="pass",
    )
    assert manifest["artifact_status"] == "blocked"
    assert "parent_lineage_status" in manifest["blocked_reason"]
    assert "parent_code_dirty" in manifest["blocked_reason"]
    assert direct_parent_gate_failures([parent])


def test_date_only_receipt_inherits_split_but_not_universe(tmp_path: Path) -> None:
    parent = build_artifact_manifest(
        stage_id="legacy_split",
        profile=Profile("full_research", ProfileType.FULL_RESEARCH),
        config={"research_run_family_id": "fixture"},
        output_files=[],
        code_state=CodeState("abc", False, ""),
        universe_artifact_id="universe:v1",
        split_manifest_id="split:stable",
        lineage_status="complete",
        artifact_status="pass",
        run_id="parent",
    )
    parent_path = tmp_path / "parent.json"
    from research_validation.lineage import write_artifact_manifest

    write_artifact_manifest(parent_path, parent)
    child = write_stage_artifact_manifest(
        project_root=tmp_path,
        stage_id="date_split_semantics_v1",
        config={
            "profile_name": "full_research",
            "profile_type": "full_research",
            "research_run_family_id": "fixture",
        },
        output_dir=tmp_path,
        output_files=[],
        input_manifest_paths=[parent_path],
        code_state=CodeState("def", False, ""),
        inherit_lineage_fields=["split_manifest_id"],
        artifact_status="pass",
    )
    assert child["artifact_status"] == "pass"
    assert child["lineage_status"] == "complete"
    assert child["split_manifest_id"] == "split:stable"
    assert child["universe_artifact_id"] is None
