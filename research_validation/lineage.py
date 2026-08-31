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
PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEGACY_FROZEN_MANIFEST_CONTRACTS = (
    PROJECT_ROOT / "configs" / "legacy_frozen_manifest_contracts_v1.json"
)
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


def git_blob_sha1(path: Path, *, repo_root: Path | None = None) -> str:
    if repo_root is not None:
        result = subprocess.run(
            ["git", "hash-object", str(path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode == 0 and len(result.stdout.strip()) == 40:
            return result.stdout.strip()
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode()
    return hashlib.sha1(header + payload).hexdigest()  # noqa: S324 - Git object identity


def git_blob_sha256(path: Path, *, repo_root: Path | None = None) -> str:
    blob_sha1 = git_blob_sha1(path, repo_root=repo_root)
    if repo_root is not None:
        result = subprocess.run(
            ["git", "cat-file", "blob", blob_sha1],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return hashlib.sha256(result.stdout).hexdigest()
    return sha256_file(path)


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


def critical_contract_failures(paths: Sequence[Path]) -> list[str]:
    failures: list[str] = []
    for path in paths:
        if not path.is_file():
            failures.append(f"missing_contract:{path.as_posix()}")
            continue
        try:
            frame = pd.read_csv(path)
        except Exception as exc:
            failures.append(f"invalid_contract:{path.as_posix()}:{exc}")
            continue
        if "status" not in frame:
            failures.append(f"contract_missing_status:{path.as_posix()}")
            continue
        severity = (
            frame["severity"].astype(str).str.lower()
            if "severity" in frame
            else pd.Series("critical", index=frame.index)
        )
        blocked = frame.loc[
            severity.eq("critical") & ~frame["status"].astype(str).str.lower().eq("pass")
        ]
        for row in blocked.itertuples(index=False):
            name = getattr(row, "check_name", "unknown_check")
            status = getattr(row, "status", "unknown")
            failures.append(f"critical_contract:{path.name}:{name}:{status}")
    return failures


def direct_parent_gate_failures(
    manifests: Sequence[Mapping[str, Any]],
    *,
    require_complete: bool = True,
    require_clean_code: bool = True,
) -> list[str]:
    failures: list[str] = []
    for manifest in manifests:
        artifact_id = str(manifest.get("artifact_id", "unknown"))
        if manifest.get("artifact_status") != "pass":
            failures.append(
                f"parent_artifact_status:{artifact_id}:{manifest.get('artifact_status')}"
            )
        if require_complete and manifest.get("lineage_status") != "complete":
            failures.append(
                f"parent_lineage_status:{artifact_id}:{manifest.get('lineage_status')}"
            )
        if require_clean_code and bool(manifest.get("code_dirty")):
            failures.append(f"parent_code_dirty:{artifact_id}")
    return failures


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
    contract_paths: Sequence[Path] | None = None,
    require_complete_parents: bool | None = None,
    inherit_lineage_fields: Sequence[str] | None = None,
) -> dict[str, Any]:
    del project_root
    inputs, missing_inputs = load_input_manifests(input_manifest_paths)
    profile = resolve_profile(config)
    strict_parents = (
        profile.type == ProfileType.FULL_RESEARCH
        if require_complete_parents is None
        else bool(require_complete_parents)
    )
    ids = {
        "universe_artifact_id": universe_artifact_id,
        "split_manifest_id": split_manifest_id,
        "factor_catalog_id": factor_catalog_id,
        "factor_frame_id": factor_frame_id,
    }
    inherited_fields = (
        set(LINEAGE_ID_FIELDS)
        if inherit_lineage_fields is None
        else {str(field) for field in inherit_lineage_fields}
    )
    unknown_inherited_fields = inherited_fields - set(LINEAGE_ID_FIELDS)
    if unknown_inherited_fields:
        raise ValueError(
            f"unknown inherited lineage fields: {sorted(unknown_inherited_fields)}"
        )
    missing = list(missing_lineage_fields)
    missing.extend(f"input_manifest:{value}" for value in missing_inputs)
    for field, value in list(ids.items()):
        if value is not None:
            continue
        if field not in inherited_fields:
            continue
        inherited, conflict = inherited_lineage_id(inputs, field)
        ids[field] = inherited
        if conflict:
            missing.append(f"inconsistent:{field}")
            lineage_status = "inconsistent"
    inferred_contracts = [
        path
        for path in output_files
        if path.suffix.lower() == ".csv" and "contract" in path.name.lower()
    ]
    gate_failures = critical_contract_failures(
        list(contract_paths) if contract_paths is not None else inferred_contracts
    )
    if strict_parents:
        gate_failures.extend(direct_parent_gate_failures(inputs))
    effective_lineage_status = lineage_status
    if effective_lineage_status is None:
        effective_lineage_status = (
            "reference_only"
            if missing and profile.type != ProfileType.FULL_RESEARCH
            else "incomplete"
            if missing
            else "complete"
        )
    if artifact_status == "pass" and effective_lineage_status != "complete":
        gate_failures.append(f"child_lineage_status:{effective_lineage_status}")
    if gate_failures and artifact_status == "pass":
        artifact_status = "blocked"
        blocked_reason = "artifact_gate:" + "|".join(sorted(set(gate_failures)))
    manifest = build_artifact_manifest(
        stage_id=stage_id,
        profile=profile,
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


def build_artifact_index(outputs_root: Path) -> tuple[
    dict[str, tuple[dict[str, Any], Path]], list[LineageIssue]
]:
    return build_artifact_index_with_contracts(outputs_root)


def _load_legacy_frozen_contracts(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported legacy frozen manifest contract schema")
    if payload.get("contract") != "legacy_frozen_non_lineage_artifact_manifests":
        raise ValueError("invalid legacy frozen manifest contract kind")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("legacy frozen manifest contracts must be a list")
    required = {
        "relative_path",
        "manifest_sha256",
        "git_blob_sha1",
        "introduced_commit",
        "stage_id",
        "manifest_schema_version",
        "stage_lifecycle",
        "closeout_validator",
        "reason",
    }
    seen_hashes: set[str] = set()
    seen_paths: set[str] = set()
    for contract in artifacts:
        if not isinstance(contract, dict) or required - set(contract):
            raise ValueError("legacy frozen manifest contract is incomplete")
        digest = str(contract["manifest_sha256"])
        relative = Path(str(contract["relative_path"])).as_posix()
        if digest in seen_hashes or relative in seen_paths:
            raise ValueError("duplicate legacy frozen manifest contract")
        if len(digest) != 64 or len(str(contract["git_blob_sha1"])) != 40:
            raise ValueError("invalid legacy frozen manifest content identity")
        if len(str(contract["introduced_commit"])) != 40:
            raise ValueError("invalid legacy frozen manifest provenance commit")
        seen_hashes.add(digest)
        seen_paths.add(relative)
    return [dict(item) for item in artifacts]


def _legacy_frozen_manifest_issues(
    *,
    manifest: Mapping[str, Any],
    path: Path,
    outputs_root: Path,
    contracts_by_hash: Mapping[str, Mapping[str, Any]],
) -> tuple[bool, list[LineageIssue]]:
    digest = git_blob_sha256(path, repo_root=outputs_root.parent)
    contract = contracts_by_hash.get(digest)
    if contract is None:
        return False, []
    stage_id = str(manifest.get("stage_id", ""))
    issues: list[LineageIssue] = []
    try:
        relative = path.resolve().relative_to(outputs_root.resolve()).as_posix()
    except ValueError:
        relative = path.resolve().as_posix()
    expected_values = {
        "relative_path": relative,
        "git_blob_sha1": git_blob_sha1(path, repo_root=outputs_root.parent),
        "stage_id": stage_id,
        "manifest_schema_version": manifest.get("schema_version"),
        "stage_lifecycle": manifest.get("stage_lifecycle"),
    }
    for field, actual in expected_values.items():
        if contract.get(field) != actual:
            issues.append(
                LineageIssue(
                    "legacy_frozen_manifest_contract",
                    "",
                    f"{relative}:{field}={actual!r};expected={contract.get(field)!r}",
                    stage_id,
                )
            )
    hashes = manifest.get("output_file_hashes")
    if not isinstance(hashes, dict) or not hashes:
        issues.append(
            LineageIssue(
                "legacy_frozen_manifest_outputs",
                "",
                f"{relative}:missing output_file_hashes",
                stage_id,
            )
        )
    else:
        for output_name, expected_hash in hashes.items():
            output_path = path.parent / Path(str(output_name))
            if not output_path.is_file():
                reason = f"{relative}:missing output {output_name}"
            elif sha256_file(output_path) != str(expected_hash):
                reason = f"{relative}:hash differs for {output_name}"
            else:
                continue
            issues.append(
                LineageIssue(
                    "legacy_frozen_manifest_outputs", "", reason, stage_id
                )
            )
    return True, issues


def build_artifact_index_with_contracts(
    outputs_root: Path,
    *,
    legacy_contracts_path: Path = LEGACY_FROZEN_MANIFEST_CONTRACTS,
) -> tuple[dict[str, tuple[dict[str, Any], Path]], list[LineageIssue]]:
    index: dict[str, tuple[dict[str, Any], Path]] = {}
    issues: list[LineageIssue] = []
    try:
        contracts = _load_legacy_frozen_contracts(legacy_contracts_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {}, [
            LineageIssue(
                "legacy_frozen_manifest_contract_registry", "", str(exc)
            )
        ]
    contracts_by_hash = {
        str(contract["manifest_sha256"]): contract for contract in contracts
    }
    for path in sorted(outputs_root.rglob("artifact_manifest.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("artifact manifest must be a mapping")
            manifest = dict(value)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            issues.append(
                LineageIssue("artifact_index_manifest_invalid", "", f"{path}:{exc}")
            )
            continue
        try:
            validate_manifest_schema(manifest)
        except ValueError as exc:
            recognized, legacy_issues = _legacy_frozen_manifest_issues(
                manifest=manifest,
                path=path,
                outputs_root=outputs_root,
                contracts_by_hash=contracts_by_hash,
            )
            if recognized:
                issues.extend(legacy_issues)
                continue
            issues.append(
                LineageIssue("artifact_index_manifest_invalid", "", f"{path}:{exc}")
            )
            continue
        artifact_id = str(manifest["artifact_id"])
        if artifact_id in index:
            issues.append(
                LineageIssue(
                    "artifact_index_duplicate_id",
                    artifact_id,
                    f"{index[artifact_id][1]}|{path}",
                    str(manifest["stage_id"]),
                )
            )
            continue
        index[artifact_id] = (manifest, path)
    return index, issues


def validate_transitive_lineage(
    *,
    outputs_root: Path,
    start_manifest_paths: Sequence[Path],
    semantics: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[LineageIssue]]:
    index, issues = build_artifact_index(outputs_root)
    stage_rules = dict(semantics.get("stage_authority", {}))
    edge_rules = dict(semantics.get("edge_authority", {}))
    queue: list[str] = []
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for path in start_manifest_paths:
        if not path.is_file():
            issues.append(LineageIssue("start_manifest_missing", "", path.as_posix()))
            continue
        try:
            queue.append(str(load_artifact_manifest(path)["artifact_id"]))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            issues.append(LineageIssue("start_manifest_invalid", "", f"{path}:{exc}"))
    visited: set[str] = set()
    while queue:
        artifact_id = queue.pop(0)
        if artifact_id in visited:
            continue
        visited.add(artifact_id)
        resolved = index.get(artifact_id)
        if resolved is None:
            issues.append(
                LineageIssue(
                    "unknown_input_artifact_id",
                    artifact_id,
                    "artifact ID cannot be uniquely resolved in repository index",
                )
            )
            continue
        manifest, path = resolved
        stage_id = str(manifest["stage_id"])
        nodes.append(
            {
                "artifact_id": artifact_id,
                "stage_id": stage_id,
                "manifest_path": path.as_posix(),
                "artifact_status": manifest["artifact_status"],
                "lineage_status": manifest["lineage_status"],
                "code_dirty": bool(manifest["code_dirty"]),
            }
        )
        issues.extend(validate_manifest_outputs(manifest, path.parent))
        for failure in direct_parent_gate_failures([manifest]):
            issues.append(
                LineageIssue("transitive_artifact_gate", artifact_id, failure, stage_id)
            )
        if stage_id not in stage_rules:
            issues.append(
                LineageIssue(
                    "unknown_stage_semantics",
                    artifact_id,
                    f"stage has no authority rule: {stage_id}",
                    stage_id,
                )
            )
        parent_values: dict[str, set[str]] = {
            field: set() for field in LINEAGE_ID_FIELDS
        }
        for parent_id in manifest["input_artifact_ids"]:
            parent_resolved = index.get(str(parent_id))
            if parent_resolved is None:
                issues.append(
                    LineageIssue(
                        "unknown_input_artifact_id",
                        artifact_id,
                        f"unknown parent: {parent_id}",
                        stage_id,
                    )
                )
                edges.append(
                    {
                        "child_artifact_id": artifact_id,
                        "child_stage_id": stage_id,
                        "parent_artifact_id": parent_id,
                        "parent_stage_id": "",
                        "authority_fields": "",
                        "status": "blocked_unknown_parent",
                    }
                )
                continue
            parent, _ = parent_resolved
            parent_stage = str(parent["stage_id"])
            override = dict(edge_rules.get(stage_id, {})).get(parent_stage)
            if override is None:
                parent_rule = stage_rules.get(parent_stage)
                authority_fields = (
                    list(parent_rule.get("authoritative_fields", []))
                    if parent_rule is not None
                    else []
                )
                mode = "authority"
            else:
                override = dict(override)
                mode = str(override.get("mode", "authority"))
                authority_fields = list(override.get("authoritative_fields", []))
            unknown_fields = set(authority_fields) - set(LINEAGE_ID_FIELDS)
            edge_status = "pass"
            if unknown_fields:
                issues.append(
                    LineageIssue(
                        "unknown_edge_authority_field",
                        artifact_id,
                        f"{parent_stage}:{sorted(unknown_fields)}",
                        stage_id,
                    )
                )
                edge_status = "blocked"
            if mode not in {"authority", "evidence_only"}:
                issues.append(
                    LineageIssue(
                        "unknown_edge_authority_mode",
                        artifact_id,
                        f"{parent_stage}:{mode}",
                        stage_id,
                    )
                )
                edge_status = "blocked"
            for field in authority_fields:
                parent_value = parent.get(field)
                if not parent_value:
                    issues.append(
                        LineageIssue(
                            "parent_authority_field_missing",
                            artifact_id,
                            f"{parent_stage}.{field}",
                            stage_id,
                        )
                    )
                    edge_status = "blocked"
                    continue
                parent_values[field].add(str(parent_value))
                if manifest.get(field) != parent_value:
                    issues.append(
                        LineageIssue(
                            "lineage_edge_incompatible",
                            artifact_id,
                            (
                                f"{field}:child={manifest.get(field)};"
                                f"parent={parent_value};parent_stage={parent_stage}"
                            ),
                            stage_id,
                        )
                    )
                    edge_status = "blocked"
            edges.append(
                {
                    "child_artifact_id": artifact_id,
                    "child_stage_id": stage_id,
                    "parent_artifact_id": parent_id,
                    "parent_stage_id": parent_stage,
                    "authority_fields": "|".join(authority_fields),
                    "status": edge_status,
                }
            )
            queue.append(str(parent_id))
        for field, values in parent_values.items():
            if len(values) > 1:
                issues.append(
                    LineageIssue(
                        "conflicting_authoritative_parent_ids",
                        artifact_id,
                        f"{field}:{sorted(values)}",
                        stage_id,
                    )
                )
    for cycle in _detect_cycles(
        [index[item][0] for item in visited if item in index]
    ):
        issues.append(LineageIssue("artifact_dag_cycle", cycle, "cycle detected"))
    return nodes, edges, issues
