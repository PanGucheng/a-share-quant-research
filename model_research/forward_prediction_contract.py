from __future__ import annotations

import hashlib
import re
import subprocess
from datetime import date, datetime, time
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

import yaml


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHANGHAI = ZoneInfo("Asia/Shanghai")
PREDICTION_PATH_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+$")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_prediction_entry_contract(path: str | Path) -> dict[str, Any]:
    candidate = Path(path)
    resolved = candidate if candidate.is_absolute() else PROJECT_ROOT / candidate
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    calendar = payload["calendar"]
    git_binding = payload["git_binding"]
    governance = payload["governance"]
    if (
        payload["contract_id"] != "forward_prediction_entry_contract_v1"
        or calendar["authority"] != "admitted_raw_snapshot_manifest"
        or not calendar["decision_date_must_exist"]
        or calendar["label_start_date"] != "program_derived_next_trading_day"
        or calendar["label_start_cutoff"]
        != "program_derived_09_25_asia_shanghai"
        or not calendar["receipt_values_are_non_authoritative"]
        or not calendar["canonical_calendar_sha256_required"]
        or not git_binding["prediction_repo_path_required"]
        or not git_binding["commit_must_exist"]
        or int(git_binding["commit_sha_length"]) != 40
        or git_binding["prediction_tree_entry_type"] != "regular_file_blob"
        or not git_binding["prediction_blob_sha256_must_match"]
        or git_binding["commit_timestamp_source"] != "git_committer_metadata"
        or not git_binding["commit_timestamp_must_precede_derived_cutoff"]
    ):
        raise ValueError("forward prediction entry contract is not fail-closed")
    if (
        governance["generate_forward_prediction"]
        or governance["read_forward_label"]
        or governance["change_candidate_freeze"]
        or not governance["forward_data_waiting"]
        or governance["production_model_selected"]
        or governance["live_trading_ready"]
    ):
        raise ValueError("forward prediction entry contract overclaims readiness")
    return payload


def _aware_timestamp(value: object, *, field: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed


def _date(value: object, *, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date") from exc


def _normalized_calendar(values: Iterable[object]) -> tuple[date, ...]:
    calendar = tuple(_date(value, field="trading_calendar") for value in values)
    if not calendar:
        raise ValueError("trading calendar is empty")
    if calendar != tuple(sorted(set(calendar))):
        raise ValueError("trading calendar must be unique and strictly increasing")
    return calendar


def derive_label_start_contract(
    *, decision_date: object, trading_calendar: Iterable[object]
) -> dict[str, str]:
    """Derive t+1 and its immutable Shanghai cutoff from the calendar."""

    decision = _date(decision_date, field="decision_date")
    calendar = _normalized_calendar(trading_calendar)
    try:
        position = calendar.index(decision)
    except ValueError as exc:
        raise PermissionError("decision_date is not in authoritative trading calendar") from exc
    if position + 1 >= len(calendar):
        raise PermissionError("authoritative trading calendar has no next trading day")
    label_start = calendar[position + 1]
    cutoff = datetime.combine(label_start, time(9, 25), tzinfo=SHANGHAI)
    canonical_payload = "\n".join(item.isoformat() for item in calendar) + "\n"
    return {
        "label_start_date": label_start.isoformat(),
        "label_start_cutoff": cutoff.isoformat(),
        "trading_calendar_sha256": hashlib.sha256(
            canonical_payload.encode("ascii")
        ).hexdigest(),
    }


def _git(repository: Path, *args: str, text: bool = True) -> str | bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=text,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = ""
        if isinstance(exc, subprocess.CalledProcessError):
            stderr = exc.stderr
            detail = stderr.strip() if isinstance(stderr, str) else stderr.decode(
                "utf-8", errors="replace"
            ).strip()
        raise ValueError(f"Git prediction receipt verification failed: {detail}") from exc
    return result.stdout


def _prediction_path(value: object) -> str:
    path = str(value)
    pure = PurePosixPath(path)
    if (
        not path
        or not PREDICTION_PATH_PATTERN.fullmatch(path)
        or "\\" in path
        or pure.is_absolute()
        or pure.as_posix() != path
        or any(part in ("", ".", "..") for part in pure.parts)
    ):
        raise ValueError("prediction_repo_path must be a safe repository-relative path")
    return pure.as_posix()


def verify_prediction_git_binding(
    *,
    repository: str | Path,
    prediction_commit_sha: object,
    prediction_repo_path: object,
    prediction_sha256: object,
) -> dict[str, str]:
    """Read a prediction blob and committer time directly from a Git commit."""

    commit = str(prediction_commit_sha)
    expected_hash = str(prediction_sha256)
    if not COMMIT_PATTERN.fullmatch(commit):
        raise ValueError("prediction_commit_sha is invalid")
    if not SHA256_PATTERN.fullmatch(expected_hash):
        raise ValueError("prediction_sha256 is invalid")
    repo = Path(repository).resolve()
    if not repo.is_dir():
        raise ValueError("prediction repository does not exist")
    resolved = str(_git(repo, "rev-parse", "--verify", f"{commit}^{{commit}}")).strip()
    if resolved != commit:
        raise ValueError("prediction commit did not resolve to the exact receipt SHA")
    repo_path = _prediction_path(prediction_repo_path)
    object_spec = f"{commit}:{repo_path}"
    tree_entry = str(
        _git(repo, "ls-tree", "--full-tree", commit, "--", repo_path)
    ).strip()
    if not tree_entry or "\t" not in tree_entry:
        raise ValueError("prediction path is absent from the receipt commit tree")
    metadata, tree_path = tree_entry.split("\t", 1)
    mode, listed_type, _object_id = metadata.split(" ", 2)
    if tree_path != repo_path or listed_type != "blob" or mode not in {
        "100644",
        "100755",
    }:
        raise ValueError("prediction commit tree entry is not a regular file blob")
    object_type = str(_git(repo, "cat-file", "-t", object_spec)).strip()
    if object_type != "blob":
        raise ValueError("prediction path is not a blob in the receipt commit")
    payload = _git(repo, "cat-file", "blob", object_spec, text=False)
    if not isinstance(payload, bytes):
        raise TypeError("Git blob reader did not return bytes")
    actual_hash = hashlib.sha256(payload).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError("prediction blob SHA256 differs from receipt")
    commit_timestamp = _aware_timestamp(
        str(_git(repo, "show", "-s", "--format=%cI", commit)).strip(),
        field="Git committer timestamp",
    )
    return {
        "prediction_commit_sha": commit,
        "prediction_repo_path": repo_path,
        "prediction_sha256": actual_hash,
        "prediction_commit_timestamp": commit_timestamp.isoformat(),
    }


def validate_forward_admission(
    *,
    decision_date: object,
    raw_snapshot_first_seen_at: object,
    candidate_freeze_effective_time: object,
) -> dict[str, object]:
    """Fail closed against post-freeze downloads of already-historical dates."""

    decision = _date(decision_date, field="decision_date")
    first_seen = _aware_timestamp(
        raw_snapshot_first_seen_at, field="raw_snapshot_first_seen_at"
    )
    freeze = _aware_timestamp(
        candidate_freeze_effective_time,
        field="candidate_freeze_effective_time",
    )
    effective_local_date = freeze.astimezone(SHANGHAI).date()
    if decision <= effective_local_date:
        raise PermissionError(
            "decision_date is not after candidate freeze effective local date"
        )
    if first_seen <= freeze:
        raise PermissionError(
            "raw snapshot was not first seen after candidate freeze timestamp"
        )
    return {
        "decision_date": decision.isoformat(),
        "candidate_freeze_effective_date_asia_shanghai": (
            effective_local_date.isoformat()
        ),
        "raw_snapshot_first_seen_at": first_seen.isoformat(),
        "admission_status": "prospective_eligible",
    }


def validate_prediction_freeze_receipt(
    receipt: Mapping[str, Any],
    *,
    candidate_freeze_effective_time: object,
    trading_calendar: Iterable[object],
    repository: str | Path,
) -> dict[str, object]:
    """Validate immutable prediction creation and publication before t+1."""

    required = {
        "decision_date",
        "raw_snapshot_first_seen_at",
        "feature_snapshot_created_at",
        "prediction_created_at",
        "prediction_sha256",
        "prediction_commit_sha",
        "prediction_repo_path",
        "prediction_commit_timestamp",
        "label_start_date",
        "label_start_cutoff",
        "trading_calendar_sha256",
        "label_mature_date",
        "label_read_count_at_prediction",
        "candidate_freeze_id",
        "model_sha256",
        "preprocessing_sha256",
    }
    missing = sorted(required - set(receipt))
    if missing:
        raise ValueError(f"prediction freeze receipt missing fields: {missing}")
    admission = validate_forward_admission(
        decision_date=receipt["decision_date"],
        raw_snapshot_first_seen_at=receipt["raw_snapshot_first_seen_at"],
        candidate_freeze_effective_time=candidate_freeze_effective_time,
    )
    decision = _date(receipt["decision_date"], field="decision_date")
    derived = derive_label_start_contract(
        decision_date=decision, trading_calendar=trading_calendar
    )
    for field in (
        "label_start_date",
        "label_start_cutoff",
        "trading_calendar_sha256",
    ):
        if str(receipt[field]) != derived[field]:
            raise PermissionError(f"receipt {field} differs from calendar-derived value")
    label_start = _date(derived["label_start_date"], field="label_start_date")
    label_mature = _date(receipt["label_mature_date"], field="label_mature_date")
    first_seen = _aware_timestamp(
        receipt["raw_snapshot_first_seen_at"],
        field="raw_snapshot_first_seen_at",
    )
    feature_created = _aware_timestamp(
        receipt["feature_snapshot_created_at"],
        field="feature_snapshot_created_at",
    )
    prediction_created = _aware_timestamp(
        receipt["prediction_created_at"], field="prediction_created_at"
    )
    git_binding = verify_prediction_git_binding(
        repository=repository,
        prediction_commit_sha=receipt["prediction_commit_sha"],
        prediction_repo_path=receipt["prediction_repo_path"],
        prediction_sha256=receipt["prediction_sha256"],
    )
    cutoff = _aware_timestamp(
        derived["label_start_cutoff"], field="label_start_cutoff"
    )
    commit_timestamp = _aware_timestamp(
        git_binding["prediction_commit_timestamp"],
        field="Git committer timestamp",
    )
    recorded_commit_timestamp = _aware_timestamp(
        receipt["prediction_commit_timestamp"],
        field="prediction_commit_timestamp",
    )
    if recorded_commit_timestamp != commit_timestamp:
        raise PermissionError(
            "receipt prediction_commit_timestamp differs from Git committer timestamp"
        )
    if not decision < label_start < label_mature:
        raise ValueError("label dates do not follow t < t+1 < t+21 ordering")
    if feature_created < first_seen:
        raise PermissionError("feature snapshot predates raw first-seen receipt")
    if prediction_created < feature_created:
        raise PermissionError("prediction predates feature snapshot")
    if prediction_created >= cutoff:
        raise PermissionError("prediction was created after label-start cutoff")
    if commit_timestamp >= cutoff:
        raise PermissionError("prediction was committed after label-start cutoff")
    if commit_timestamp < prediction_created:
        raise PermissionError("prediction commit predates prediction payload")
    if int(receipt["label_read_count_at_prediction"]) != 0:
        raise PermissionError("prediction stage read forward labels")
    for field in ("model_sha256", "preprocessing_sha256"):
        if not SHA256_PATTERN.fullmatch(str(receipt[field])):
            raise ValueError(f"{field} is invalid")
    if not str(receipt["candidate_freeze_id"]).startswith(
        "forward-candidate-freeze:"
    ):
        raise ValueError("candidate_freeze_id is invalid")
    return {
        **admission,
        "prediction_created_at": prediction_created.isoformat(),
        "prediction_commit_timestamp": commit_timestamp.isoformat(),
        "label_start_cutoff": cutoff.isoformat(),
        "label_start_date": label_start.isoformat(),
        "trading_calendar_sha256": derived["trading_calendar_sha256"],
        "prediction_repo_path": git_binding["prediction_repo_path"],
        "prediction_sha256": git_binding["prediction_sha256"],
        "prediction_freeze_status": "immutable_before_label_start",
    }
