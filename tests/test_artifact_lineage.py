from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from research_validation.lineage import (
    CodeState,
    build_artifact_manifest,
    validate_lineage_chain,
    validate_current_upstream_ids,
    write_artifact_manifest,
)
from research_validation.profiles import Profile, ProfileType


def manifest(tmp_path: Path, *, stage: str = "stage", profile_type: ProfileType = ProfileType.REFERENCE, inputs=(), **kwargs):
    output = tmp_path / f"{stage}.csv"
    output.write_text("a\n1\n", encoding="utf-8")
    return build_artifact_manifest(
        stage_id=stage,
        profile=Profile("local_reference" if profile_type == ProfileType.REFERENCE else "full_research", profile_type),
        config={"value": kwargs.pop("config_value", 1)},
        output_files=[output],
        code_state=CodeState("abc123", False, ""),
        input_manifests=list(inputs),
        created_at=datetime(2026, 7, 13, tzinfo=timezone.utc),
        run_id=f"run-{stage}",
        **kwargs,
    )


def test_artifact_id_is_content_stable_and_config_sensitive(tmp_path: Path) -> None:
    first = manifest(tmp_path, stage="one", missing_lineage_fields=["factor_frame_id"])
    second = manifest(tmp_path, stage="one", missing_lineage_fields=["factor_frame_id"])
    changed = manifest(tmp_path, stage="one", missing_lineage_fields=["factor_frame_id"], config_value=2)
    assert first["artifact_id"] == second["artifact_id"]
    assert first["artifact_id"] != changed["artifact_id"]
    assert first["lineage_status"] == "reference_only"
    path = tmp_path / "artifact_manifest.json"
    write_artifact_manifest(path, first)
    assert path.is_file()


def test_lineage_mismatch_and_unknown_input_block_full_gate(tmp_path: Path) -> None:
    parent = manifest(
        tmp_path,
        stage="parent",
        profile_type=ProfileType.FULL_RESEARCH,
        universe_artifact_id="universe:a",
        split_manifest_id="split:a",
        factor_catalog_id="catalog:a",
        factor_frame_id="frame:a",
        start_date="2020-01-01",
        end_date="2024-12-31",
    )
    child = manifest(
        tmp_path,
        stage="child",
        profile_type=ProfileType.FULL_RESEARCH,
        inputs=[parent],
        universe_artifact_id="universe:b",
        split_manifest_id="split:a",
        factor_catalog_id="catalog:a",
        factor_frame_id="frame:a",
        start_date="2021-01-01",
        end_date="2023-12-31",
    )
    child["input_artifact_ids"].append("missing:artifact")
    issues = validate_lineage_chain(
        [parent, child],
        profile_gate="full_research",
        require_complete=True,
        require_known_inputs=True,
        require_consistent_ids=True,
    )
    assert {issue.check_name for issue in issues} >= {"upstream_traceability", "universe_artifact_id"}


def test_lineage_cycle_and_date_range_are_detected(tmp_path: Path) -> None:
    first = manifest(tmp_path, stage="first", start_date="2021-01-01", end_date="2022-12-31")
    second = manifest(tmp_path, stage="second", inputs=[first], start_date="2020-01-01", end_date="2023-12-31")
    first["input_artifact_ids"] = [second["artifact_id"]]
    issues = validate_lineage_chain(
        [first, second],
        profile_gate="reference",
        require_complete=False,
        require_known_inputs=True,
        require_consistent_ids=False,
    )
    assert {issue.check_name for issue in issues} >= {"artifact_dag_cycle", "date_range_compatibility"}


def test_current_upstream_id_change_marks_child_stale(tmp_path: Path) -> None:
    old_parent = manifest(tmp_path, stage="parent", config_value=1)
    child = manifest(tmp_path, stage="child", inputs=[old_parent])
    current_parent = manifest(tmp_path, stage="parent", config_value=2)
    issues = validate_current_upstream_ids([current_parent, child], {"child": ["parent"]})
    assert {issue.check_name for issue in issues} == {"stale_upstream_artifact"}


def test_full_research_profile_names_must_match(tmp_path: Path) -> None:
    first = manifest(tmp_path, stage="first", profile_type=ProfileType.FULL_RESEARCH, research_run_family_id="family")
    second = manifest(tmp_path, stage="second", profile_type=ProfileType.FULL_RESEARCH, research_run_family_id="family")
    second["profile_name"] = "full_research_b"
    issues = validate_lineage_chain([first, second], profile_gate="full_research", require_complete=True, require_known_inputs=False, require_consistent_ids=True)
    assert "full_profile_name_homogeneity" in {issue.check_name for issue in issues}
