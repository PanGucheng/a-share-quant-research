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

from .profiles import Profile, ProfileType, assert_profiles_compatible, resolve_profile


MANIFEST_SCHEMA_VERSION = 2
V1_REQUIRED_MANIFEST_FIELDS = frozenset(
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
V2_REQUIRED_MANIFEST_FIELDS = V1_REQUIRED_MANIFEST_FIELDS | frozenset(
    {"artifact_status", "blocked_reason", "research_run_family_id", "producer_run_id"}
)
LINEAGE_ID_FIELDS = (
    "universe_artifact_id",
    "split_manifest_id",
    "factor_catalog_id",
    "factor_frame_id",
)
VALID_LINEAGE_STATUSES = {"complete", "reference_only", "incomplete", "inconsistent"}
VALID_ARTIFACT_STATUSES = {"pass", "blocked", "failed"}


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
    pathspec = ("--", ".", ":(exclude)outputs", ":(exclude)tmp", ":(exclude).pytest_cache")
    status = _git(repo_root, "status", "--short", "--untracked-files=normal", *pathspec)
    diff = _git(repo_root, "diff", "--binary", "HEAD", *pathspec) if status else ""
    state = f"{status}\n{diff}" if status else ""
    return CodeState(commit_sha=commit, dirty=bool(status), diff_sha256=sha256_text(state) if state else "")


def content_reference_id(kind: str, paths: Sequence[Path]) -> str:
    entries = [(path.name, sha256_file(path)) for path in sorted(paths, key=lambda item: item.as_posix())]
    return f"{kind}:{sha256_text(canonical_json(entries))}"


def _normalized_date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return pd.Timestamp(value).date().isoformat()


def _output_hashes(paths: Sequence[Path], output_dir: Path | None) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(paths, key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        try:
            key = path.resolve().relative_to(output_dir.resolve()).as_posix() if output_dir else path.name
        except ValueError:
            key = path.name
        if key in hashes:
            raise ValueError(f"duplicate output manifest key: {key}")
        hashes[key] = sha256_file(path)
    return hashes


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
    output_dir: Path | None = None,
    artifact_status: str = "pass",
    blocked_reason: str = "",
    research_run_family_id: str | None = None,
) -> dict[str, Any]:
    missing = sorted(set(str(item) for item in missing_lineage_fields))
    if lineage_status is None:
        if missing:
            lineage_status = "reference_only" if profile.type != ProfileType.FULL_RESEARCH else "incomplete"
        else:
            lineage_status = "complete"
    if lineage_status not in VALID_LINEAGE_STATUSES:
        raise ValueError(f"invalid lineage_status: {lineage_status}")
    if artifact_status not in VALID_ARTIFACT_STATUSES:
        raise ValueError(f"invalid artifact_status: {artifact_status}")
    if artifact_status == "blocked" and not blocked_reason:
        raise ValueError("blocked artifact requires blocked_reason")

    timestamp = created_at or datetime.now(timezone.utc)
    effective_run_id = run_id or f"{timestamp:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
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
        "output_file_hashes": _output_hashes(output_files, output_dir),
        "missing_lineage_fields": missing,
        "artifact_status": artifact_status,
        "blocked_reason": blocked_reason,
        "research_run_family_id": research_run_family_id or str(config.get("research_run_family_id", profile.name)),
    }
    artifact_id = f"{stage_id}:{sha256_text(canonical_json(core))}"
    return {
        **core,
        "artifact_id": artifact_id,
        "run_id": effective_run_id,
        "producer_run_id": effective_run_id,
        "created_at": timestamp.isoformat(),
    }


def write_artifact_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    validate_manifest_schema(manifest)
    path.write_text(json.dumps(dict(manifest), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_artifact_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest_schema(value)
    return value


def load_input_manifests(paths: Sequence[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    manifests: list[dict[str, Any]] = []
    missing: list[str] = []
    for path in paths:
        if path.is_file():
            manifests.append(load_artifact_manifest(path))
        else:
            missing.append(path.as_posix())
    return manifests, missing


def inherited_lineage_id(input_manifests: Sequence[Mapping[str, Any]], field: str) -> tuple[str | None, bool]:
    if field not in LINEAGE_ID_FIELDS:
        raise ValueError(f"not a lineage id field: {field}")
    values = {str(item[field]) for item in input_manifests if item.get(field)}
    if len(values) == 1:
        return next(iter(values)), False
    return None, len(values) > 1


def write_stage_artifact_manifest(
    *,
    project_root: Path,
    stage_id: str,
    config: Mapping[str, Any],
    output_dir: Path,
    output_files: Sequence[Path],
    code_state: CodeState,
    input_manifest_paths: Sequence[Path] = (),
    universe_artifact_id: str | None = None,
    split_manifest_id: str | None = None,
    factor_catalog_id: str | None = None,
    factor_frame_id: str | None = None,
    start_date: Any = None,
    end_date: Any = None,
    missing_lineage_fields: Sequence[str] = (),
    lineage_status: str | None = None,
    artifact_status: str = "pass",
    blocked_reason: str = "",
) -> dict[str, Any]:
    del project_root
    inputs, missing_inputs = load_input_manifests(input_manifest_paths)
    ids = {
        "universe_artifact_id": universe_artifact_id,
        "split_manifest_id": split_manifest_id,
        "factor_catalog_id": factor_catalog_id,
        "factor_frame_id": factor_frame_id,
    }
    missing = list(missing_lineage_fields)
    missing.extend(f"input_manifest:{value}" for value in missing_inputs)
    for field, value in list(ids.items()):
        if value is not None:
            continue
        inherited, conflict = inherited_lineage_id(inputs, field)
        ids[field] = inherited
        if conflict:
            missing.append(f"inconsistent:{field}")
            lineage_status = "inconsistent"
    manifest = build_artifact_manifest(
        stage_id=stage_id,
        profile=resolve_profile(config),
        config=config,
        output_files=output_files,
        code_state=code_state,
        input_manifests=inputs,
        start_date=start_date,
        end_date=end_date,
        missing_lineage_fields=missing,
        lineage_status=lineage_status,
        output_dir=output_dir,
        artifact_status=artifact_status,
        blocked_reason=blocked_reason,
        **ids,
    )
    write_artifact_manifest(output_dir / "artifact_manifest.json", manifest)
    return manifest


def validate_manifest_schema(manifest: Mapping[str, Any]) -> None:
    version = int(manifest.get("schema_version", 0))
    required = V1_REQUIRED_MANIFEST_FIELDS if version == 1 else V2_REQUIRED_MANIFEST_FIELDS if version == 2 else frozenset()
    if not required:
        raise ValueError(f"unsupported artifact manifest schema_version: {version}")
    missing = required - set(manifest)
    if missing:
        raise ValueError(f"artifact manifest missing fields: {sorted(missing)}")
    ProfileType(str(manifest["profile_type"]))
    if manifest["lineage_status"] not in VALID_LINEAGE_STATUSES:
        raise ValueError(f"invalid lineage_status: {manifest['lineage_status']}")
    if not isinstance(manifest["input_artifact_ids"], list):
        raise ValueError("input_artifact_ids must be a list")
    if not isinstance(manifest["output_file_hashes"], dict):
        raise ValueError("output_file_hashes must be a mapping")
    if version == 2:
        if manifest["artifact_status"] not in VALID_ARTIFACT_STATUSES:
            raise ValueError(f"invalid artifact_status: {manifest['artifact_status']}")
        if manifest["artifact_status"] == "blocked" and not manifest["blocked_reason"]:
            raise ValueError("blocked artifact requires blocked_reason")
        if manifest["producer_run_id"] != manifest["run_id"]:
            raise ValueError("producer_run_id must equal run_id")


@dataclass(frozen=True)
class LineageIssue:
    check_name: str
    artifact_id: str
    reason: str
    stage_id: str = ""
    severity: str = "critical"


def validate_manifest_outputs(
    manifest: Mapping[str, Any],
    output_dir: Path,
    *,
    config: Mapping[str, Any] | None = None,
    controlled_outputs: Sequence[str] | None = None,
) -> list[LineageIssue]:
    stage_id = str(manifest.get("stage_id", ""))
    artifact_id = str(manifest.get("artifact_id", ""))
    issues: list[LineageIssue] = []
    try:
        validate_manifest_schema(manifest)
    except ValueError as exc:
        return [LineageIssue("manifest_schema", artifact_id, str(exc), stage_id)]
    if int(manifest["schema_version"]) < 2:
        issues.append(LineageIssue("manifest_freshness_schema", artifact_id, "schema v1 is read-only legacy evidence and cannot prove freshness", stage_id))
        return issues
    if config is not None and str(manifest["config_sha256"]) != config_sha256(config):
        issues.append(LineageIssue("config_sha256", artifact_id, "current config hash differs from manifest", stage_id))
    recorded = dict(manifest["output_file_hashes"])
    for relative, expected in recorded.items():
        path = output_dir / Path(relative)
        if not path.is_file():
            issues.append(LineageIssue("output_file_missing", artifact_id, f"missing output: {relative}", stage_id))
        elif sha256_file(path) != expected:
            issues.append(LineageIssue("output_hash_mismatch", artifact_id, f"hash differs: {relative}", stage_id))
    if controlled_outputs is not None:
        allowed = {Path(item).as_posix() for item in controlled_outputs}
        unexpected = sorted(set(recorded) - allowed)
        for relative in unexpected:
            issues.append(LineageIssue("uncontrolled_manifest_output", artifact_id, f"not in controlled output set: {relative}", stage_id))
    return issues


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


def validate_current_upstream_ids(
    manifests: Iterable[Mapping[str, Any]],
    required_edges: Mapping[str, Sequence[str]],
) -> list[LineageIssue]:
    values = [dict(item) for item in manifests]
    by_stage: dict[str, list[dict[str, Any]]] = {}
    for item in values:
        by_stage.setdefault(str(item.get("stage_id", "")), []).append(item)
    issues: list[LineageIssue] = []
    for stage_id, items in by_stage.items():
        if len(items) > 1:
            issues.append(LineageIssue("duplicate_current_stage", "", f"multiple current manifests for stage: {stage_id}", stage_id))
    current = {stage: items[0] for stage, items in by_stage.items() if len(items) == 1}
    for child_stage, parent_stages in required_edges.items():
        child = current.get(child_stage)
        if child is None:
            issues.append(LineageIssue("current_stage_missing", "", f"missing current manifest: {child_stage}", child_stage))
            continue
        actual = set(str(value) for value in child.get("input_artifact_ids", []))
        for parent_stage in parent_stages:
            parent = current.get(parent_stage)
            if parent is None:
                issues.append(LineageIssue("current_upstream_missing", str(child.get("artifact_id", "")), f"missing current upstream stage: {parent_stage}", child_stage))
            elif str(parent["artifact_id"]) not in actual:
                issues.append(LineageIssue("stale_upstream_artifact", str(child.get("artifact_id", "")), f"does not reference current {parent_stage}: {parent['artifact_id']}", child_stage))
    return issues


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
    if profile_gate in {"full_research", "core_model", "model_comparison"}:
        profile_names = {str(item["profile_name"]) for item in values}
        if len(profile_names) > 1:
            issues.append(LineageIssue("full_profile_name_homogeneity", "", f"mixed profile names: {sorted(profile_names)}"))
        run_families = {str(item.get("research_run_family_id", "")) for item in values}
        if "" in run_families or len(run_families) > 1:
            issues.append(LineageIssue("research_run_family_homogeneity", "", f"mixed or missing run families: {sorted(run_families)}"))

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
    for item in values:
        if item.get("artifact_status", "pass") != "pass":
            issues.append(LineageIssue("artifact_status", str(item["artifact_id"]), f"status={item.get('artifact_status')};reason={item.get('blocked_reason', '')}", str(item["stage_id"])))
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
