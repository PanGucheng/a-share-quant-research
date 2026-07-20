from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from research_validation.lineage import (
    CodeState,
    build_artifact_manifest,
    capture_code_state,
    validate_manifest_outputs,
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
