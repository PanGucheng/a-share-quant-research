from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from .profiles import Profile, ProfileType, assert_profiles_compatible


MANIFEST_SCHEMA_VERSION = 1
REQUIRED_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "artifact_id",
        "stage_id",
        "run_id",
        "profile_name",
        "profile_type",
        "lineage_status",
        "config_sha256",
        "code_commit_sha",
        "code_dirty",
        "universe_artifact_id",
        "split_manifest_id",
        "factor_catalog_id",
        "factor_frame_id",
        "input_artifact_ids",
        "start_date",
        "end_date",
        "created_at",
        "output_file_hashes",
        "missing_lineage_fields",
    }
)
LINEAGE_ID_FIELDS = (
    "universe_artifact_id",
    "split_manifest_id",
    "factor_catalog_id",
    "factor_frame_id",
)
VALID_LINEAGE_STATUSES = {"complete", "reference_only", "incomplete", "inconsistent"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def config_sha256(config: Mapping[str, Any]) -> str:
    return sha256_text(canonical_json(dict(config)))


@dataclass(frozen=True)
class CodeState:
    commit_sha: str
    dirty: bool
    diff_sha256: str


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def capture_code_state(repo_root: Path) -> CodeState:
    commit = _git(repo_root, "rev-parse", "HEAD")
    status = _git(repo_root, "status", "--short", "--untracked-files=no")
    diff = _git(repo_root, "diff", "--binary", "HEAD") if status else ""
    return CodeState(commit_sha=commit, dirty=bool(status), diff_sha256=sha256_text(diff) if diff else "")


def content_reference_id(kind: str, paths: Sequence[Path]) -> str:
    entries = [(path.name, sha256_file(path)) for path in sorted(paths, key=lambda item: item.as_posix())]
    return f"{kind}:{sha256_text(canonical_json(entries))}"


def _normalized_date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return pd.Timestamp(value).date().isoformat()


def _output_hashes(paths: Sequence[Path]) -> dict[str, str]:
    return {path.name: sha256_file(path) for path in sorted(paths, key=lambda item: item.name) if path.is_file()}


def build_artifact_manifest(
    *,
    stage_id: str,
    profile: Profile,
    config: Mapping[str, Any],
    output_files: Sequence[Path],
    code_state: CodeState,
    input_manifests: Sequence[Mapping[str, Any]] = (),
    universe_artifact_id: str | None = None,
    split_manifest_id: str | None = None,
    factor_catalog_id: str | None = None,
    factor_frame_id: str | None = None,
    start_date: Any = None,
    end_date: Any = None,
    missing_lineage_fields: Sequence[str] = (),
    lineage_status: str | None = None,
    created_at: datetime | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    missing = sorted(set(str(item) for item in missing_lineage_fields))
    if lineage_status is None:
        if missing:
            lineage_status = "reference_only" if profile.type != ProfileType.FULL_RESEARCH else "incomplete"
        else:
            lineage_status = "complete"
    if lineage_status not in VALID_LINEAGE_STATUSES:
        raise ValueError(f"invalid lineage_status: {lineage_status}")

    timestamp = created_at or datetime.now(timezone.utc)
    core = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "stage_id": stage_id,
        "profile_name": profile.name,
        "profile_type": profile.type.value,
        "lineage_status": lineage_status,
        "config_sha256": config_sha256(config),
        "code_commit_sha": code_state.commit_sha,
        "code_dirty": code_state.dirty,
        "code_diff_sha256": code_state.diff_sha256,
        "universe_artifact_id": universe_artifact_id,
        "split_manifest_id": split_manifest_id,
        "factor_catalog_id": factor_catalog_id,
        "factor_frame_id": factor_frame_id,
        "input_artifact_ids": sorted(
            {str(item["artifact_id"]) for item in input_manifests if item.get("artifact_id")}
        ),
        "start_date": _normalized_date(start_date),
        "end_date": _normalized_date(end_date),
        "output_file_hashes": _output_hashes(output_files),
        "missing_lineage_fields": missing,
    }
    artifact_id = f"{stage_id}:{sha256_text(canonical_json(core))}"
    return {
        **core,
        "artifact_id": artifact_id,
        "run_id": run_id or f"{timestamp:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}",
        "created_at": timestamp.isoformat(),
    }


def write_artifact_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    validate_manifest_schema(manifest)
    path.write_text(json.dumps(dict(manifest), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_artifact_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest_schema(value)
    return value


def validate_manifest_schema(manifest: Mapping[str, Any]) -> None:
    missing = REQUIRED_MANIFEST_FIELDS - set(manifest)
    if missing:
        raise ValueError(f"artifact manifest missing fields: {sorted(missing)}")
    ProfileType(str(manifest["profile_type"]))
    if manifest["lineage_status"] not in VALID_LINEAGE_STATUSES:
        raise ValueError(f"invalid lineage_status: {manifest['lineage_status']}")
    if not isinstance(manifest["input_artifact_ids"], list):
        raise ValueError("input_artifact_ids must be a list")
    if not isinstance(manifest["output_file_hashes"], dict):
        raise ValueError("output_file_hashes must be a mapping")


@dataclass(frozen=True)
class LineageIssue:
    check_name: str
    artifact_id: str
    reason: str


def _manifest_profile(manifest: Mapping[str, Any]) -> Profile:
    return Profile(str(manifest["profile_name"]), ProfileType(str(manifest["profile_type"])))


def _detect_cycles(manifests: Sequence[Mapping[str, Any]]) -> list[str]:
    graph = {str(item["artifact_id"]): [str(value) for value in item["input_artifact_ids"]] for item in manifests}
    visiting: set[str] = set()
    visited: set[str] = set()
    cycles: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            cycles.add(node)
            return
        if node in visited or node not in graph:
            return
        visiting.add(node)
        for parent in graph[node]:
            visit(parent)
        visiting.remove(node)
        visited.add(node)

    for artifact_id in graph:
        visit(artifact_id)
    return sorted(cycles)


def validate_lineage_chain(
    manifests: Iterable[Mapping[str, Any]],
    *,
    profile_gate: str,
    require_complete: bool,
    require_known_inputs: bool,
    require_consistent_ids: bool,
    require_clean_code: bool = False,
) -> list[LineageIssue]:
    values = [dict(item) for item in manifests]
    issues: list[LineageIssue] = []
    for item in values:
        try:
            validate_manifest_schema(item)
        except ValueError as exc:
            issues.append(LineageIssue("manifest_schema", str(item.get("artifact_id", "")), str(exc)))
    if issues:
        return issues

    try:
        assert_profiles_compatible([_manifest_profile(item) for item in values], profile_gate)
    except ValueError as exc:
        issues.append(LineageIssue("profile_compatibility", "", str(exc)))

    known = {str(item["artifact_id"]): item for item in values}
    if require_known_inputs:
        for item in values:
            for parent in item["input_artifact_ids"]:
                if parent not in known:
                    issues.append(LineageIssue("upstream_traceability", str(item["artifact_id"]), f"unknown input artifact: {parent}"))

    for cycle in _detect_cycles(values):
        issues.append(LineageIssue("artifact_dag_cycle", cycle, "artifact lineage graph contains a cycle"))

    if require_complete:
        for item in values:
            if item["lineage_status"] != "complete":
                issues.append(LineageIssue("lineage_complete", str(item["artifact_id"]), f"status={item['lineage_status']}"))
    if require_clean_code:
        for item in values:
            if bool(item["code_dirty"]):
                issues.append(LineageIssue("clean_code", str(item["artifact_id"]), "full-research artifact was produced from a dirty tree"))

    if require_consistent_ids:
        for field in LINEAGE_ID_FIELDS:
            ids = {str(item[field]) for item in values if item.get(field)}
            if len(ids) > 1:
                issues.append(LineageIssue(field, "", f"inconsistent values: {sorted(ids)}"))

    for child in values:
        child_start = pd.Timestamp(child["start_date"]) if child.get("start_date") else None
        child_end = pd.Timestamp(child["end_date"]) if child.get("end_date") else None
        for parent_id in child["input_artifact_ids"]:
            parent = known.get(parent_id)
            if parent is None or child_start is None or child_end is None:
                continue
            parent_start = pd.Timestamp(parent["start_date"]) if parent.get("start_date") else None
            parent_end = pd.Timestamp(parent["end_date"]) if parent.get("end_date") else None
            if parent_start is not None and child_start < parent_start:
                issues.append(LineageIssue("date_range_compatibility", str(child["artifact_id"]), f"starts before input {parent_id}"))
            if parent_end is not None and child_end > parent_end:
                issues.append(LineageIssue("date_range_compatibility", str(child["artifact_id"]), f"ends after input {parent_id}"))
    return issues
