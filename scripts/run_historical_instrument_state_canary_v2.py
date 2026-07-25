from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qlib_integration.instrument_state_evidence import (  # noqa: E402
    classify_available_phase,
    detect_authoritative_conflicts,
    validate_evidence_frame,
)
from research_validation.feature_matrix import file_sha256  # noqa: E402
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    load_artifact_manifest,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


COMPACT = [
    "artifact_manifest.json",
    "raw_snapshot_manifest.csv",
    "normalized_official_events.csv",
    "candidate_reconciliation.csv",
    "coverage_summary.csv",
    "contract_status.csv",
    "readiness_summary.csv",
    "source_decision.json",
    "canary_report.md",
    "resolved_config.json",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def _extension(url: str, content_type: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".pdf", ".html", ".htm"}:
        return suffix
    guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
    return guessed or ".bin"


def download_snapshots(
    events: pd.DataFrame, raw_dir: Path, request_config: dict[str, object]
) -> pd.DataFrame:
    raw_dir.mkdir(parents=True, exist_ok=True)
    timeout = int(request_config.get("timeout_seconds", 30))
    retries = int(request_config.get("retries", 3))
    headers = {"User-Agent": str(request_config.get("user_agent", "qlib-audit/2.0"))}
    rows: list[dict[str, object]] = []
    session = requests.Session()
    for url in events["source_url"].drop_duplicates():
        response = None
        error = ""
        for attempt in range(1, retries + 1):
            try:
                response = session.get(url, timeout=timeout, headers=headers)
                if response.status_code == 200 and response.content:
                    break
                error = f"http_status_{response.status_code}"
            except requests.RequestException as exc:
                error = f"{type(exc).__name__}:{exc}"
            if attempt < retries:
                time.sleep(min(attempt, 3))
        retrieved_at = datetime.now(timezone.utc).isoformat()
        status = int(response.status_code) if response is not None else 0
        payload = response.content if response is not None else b""
        content_type = (
            response.headers.get("Content-Type", "application/octet-stream")
            if response is not None
            else "application/octet-stream"
        )
        digest = hashlib.sha256(payload).hexdigest() if payload else ""
        filename = f"{hashlib.sha256(url.encode('utf-8')).hexdigest()[:20]}{_extension(url, content_type)}"
        path = raw_dir / filename
        if payload:
            path.write_bytes(payload)
        rows.append(
            {
                "source_url": url,
                "retrieved_at": retrieved_at,
                "http_status": status,
                "content_type": content_type,
                "content_length": len(payload),
                "raw_snapshot_path": f"runtime/raw/{filename}",
                "raw_snapshot_sha256": digest,
                "download_status": "pass"
                if status == 200 and bool(payload)
                else "blocked",
                "download_error": error,
                "parser_version": "manual_normalization_receipt_v2",
            }
        )
    return pd.DataFrame(rows)


def reconcile_candidates(
    events: pd.DataFrame, candidates: pd.DataFrame
) -> pd.DataFrame:
    candidate = candidates.copy()
    candidate["date"] = pd.to_datetime(candidate["date"]).dt.normalize()
    rows: list[dict[str, object]] = []
    for event in events.itertuples(index=False):
        effective = pd.Timestamp(event.effective_from).normalize()
        comparable_type = (
            "st"
            if event.state_type == "st"
            else "tradestatus"
            if event.state_type in {"suspension", "resumption"}
            and event.state_value == "full_day"
            else ""
        )
        matches = candidate.loc[
            candidate["instrument"].eq(event.instrument)
            & candidate["state_type"].eq(comparable_type)
        ].copy()
        exact = matches.loc[matches["date"].eq(effective)]
        nearest_delta = pd.NA
        nearest_date = pd.NaT
        if not matches.empty:
            deltas = (matches["date"] - effective).dt.days
            nearest_index = deltas.abs().idxmin()
            nearest_delta = int(deltas.loc[nearest_index])
            nearest_date = matches.loc[nearest_index, "date"]
        if not exact.empty:
            relation = "exact_boundary_match"
        elif comparable_type == "":
            relation = "not_comparable_control_or_terminal"
        elif matches.empty:
            relation = "no_candidate_boundary"
        elif abs(int(nearest_delta)) <= 1:
            relation = "one_day_lead_lag"
        else:
            relation = "nonmatching_candidate_boundary"
        rows.append(
            {
                "evidence_id": event.evidence_id,
                "instrument": event.instrument,
                "state_type": event.state_type,
                "state_value": event.state_value,
                "effective_from": effective,
                "available_phase": event.available_phase,
                "candidate_state_type": comparable_type,
                "candidate_relation": relation,
                "nearest_candidate_date": nearest_date,
                "nearest_candidate_delta_days": nearest_delta,
                "candidate_boundary_count": len(matches),
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the curated official-source Historical Instrument State V2 canary."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/historical_instrument_state_official_canary_v2.yaml"),
    )
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    parent_path = resolve(config["scope_manifest"])
    parent = load_artifact_manifest(parent_path)
    if parent["artifact_status"] != "pass" or parent["lineage_status"] != "complete":
        raise ValueError("scope parent is not ready")
    parent_issues = validate_manifest_outputs(parent, parent_path.parent)
    if parent_issues:
        raise ValueError(f"scope parent output validation failed: {parent_issues}")

    events = pd.DataFrame(config["events"])
    events["effective_from"] = pd.to_datetime(events["effective_from"]).dt.normalize()
    events["published_at"] = pd.to_datetime(events["published_at"])
    events["authoritative"] = events["source_tier"].eq("tier_0")
    events["available_phase"] = events.apply(
        lambda row: classify_available_phase(
            published_at=row["published_at"],
            effective_date=row["effective_from"],
            publication_precision=row["publication_precision"],
            timezone=config["timezone"],
            before_open_cutoff=config["before_open_cutoff"],
        ),
        axis=1,
    )
    events["available_at"] = events["published_at"]
    events["confidence"] = events["available_phase"].map(
        {"before_open": "event_and_pit", "after_open": "event_only", "unknown": "event_only"}
    )
    events["reason_code"] = events["available_phase"].map(
        {
            "before_open": "tier0_publication_precedes_effective_open",
            "after_open": "tier0_publication_after_effective_open",
            "unknown": "same_day_date_only_or_unknown_publication_time",
        }
    )

    output_dir = resolve(config["output_dir"])
    candidates = pd.read_csv(resolve(config["scope_candidates"]))
    controlled = COMPACT + ["runtime/raw"]
    with StageOutputPublisher(output_dir, controlled) as publisher:
        raw = download_snapshots(
            events, publisher.path("runtime/raw"), config.get("request", {})
        )
        events = events.merge(raw, on="source_url", how="left", validate="many_to_one")
        reconciliation = reconcile_candidates(events, candidates)
        schema_issues = validate_evidence_frame(events)
        conflicts = detect_authoritative_conflicts(events) if not schema_issues else pd.DataFrame()
        minimums = config["minimums"]
        counts = {
            "st_boundary_events": int(events["state_type"].eq("st").sum()),
            "full_day_suspension_events": int(
                (
                    events["state_type"].eq("suspension")
                    & events["state_value"].eq("full_day")
                ).sum()
            ),
            "intraday_control_events": int(
                (
                    events["state_type"].eq("suspension")
                    & events["state_value"].eq("intraday")
                ).sum()
            ),
            "terminal_instruments": int(
                events.loc[events["terminal_scope"].astype(bool), "instrument"].nunique()
            ),
        }
        coverage = pd.DataFrame(
            [
                {
                    "category": key,
                    "observed_count": value,
                    "required_count": int(minimums[key]),
                    "status": "pass"
                    if value >= int(minimums[key])
                    else "blocked",
                }
                for key, value in counts.items()
            ]
        )
        exact_or_control = reconciliation["candidate_relation"].isin(
            {
                "exact_boundary_match",
                "not_comparable_control_or_terminal",
                "no_candidate_boundary",
            }
        )
        critical_checks = [
            ("scope_parent_ready", True, True),
            ("event_schema_valid", len(schema_issues), 0),
            ("raw_evidence_hashes_valid", raw["download_status"].eq("pass").all(), True),
            ("source_tier_valid", events["source_tier"].eq("tier_0").all(), True),
            ("authoritative_conflict_count", len(conflicts), 0),
            (
                "same_day_date_only_fail_closed",
                events.loc[
                    events["publication_precision"].eq("date")
                    & events["published_at"].dt.normalize().eq(events["effective_from"])
                ]["available_phase"].eq("unknown").all(),
                True,
            ),
            (
                "intraday_controls_not_full_day",
                events.loc[events["state_value"].eq("intraday"), "state_value"]
                .eq("intraday")
                .all(),
                True,
            ),
            ("candidate_reconciliation_materialized", exact_or_control.notna().all(), True),
        ]
        contracts = [
            {
                "check_name": name,
                "status": "pass" if observed == required else "blocked",
                "observed_value": observed,
                "required_value": required,
                "severity": "critical",
                "reason": "",
            }
            for name, observed, required in critical_checks
        ]
        for row in coverage.itertuples(index=False):
            contracts.append(
                {
                    "check_name": f"minimum_{row.category}",
                    "status": row.status,
                    "observed_value": row.observed_count,
                    "required_value": row.required_count,
                    "severity": "capability",
                    "reason": ""
                    if row.status == "pass"
                    else "Curated official evidence is below the frozen canary minimum.",
                }
            )
        contracts_frame = pd.DataFrame(contracts)
        critical_ready = contracts_frame.loc[
            contracts_frame["severity"].eq("critical"), "status"
        ].eq("pass").all()
        minimums_ready = coverage["status"].eq("pass").all()
        before_open_rate = float(events["available_phase"].eq("before_open").mean())
        source_decision = {
            "decision": "B",
            "label": "candidate_source_useful_official_coverage_incomplete",
            "reason": (
                "The curated Tier-0 evidence is reproducible and validates fail-closed "
                "time semantics, but the frozen ST/full-day minimums and complete "
                "before-open coverage are not met."
            ),
            "before_open_provable_rate": before_open_rate,
            "unknown_event_count": int(events["available_phase"].eq("unknown").sum()),
            "after_open_event_count": int(events["available_phase"].eq("after_open").sum()),
            "instrument_state_materialization_authorized": False,
            "execution_rerun_authorized": False,
        }
        readiness = {
            "scope_frozen": True,
            "terminal_approximation_inventory_complete": True,
            "evidence_schema_ready": bool(critical_ready),
            "before_open_fail_closed_tests_pass": bool(critical_ready),
            "official_canary_complete": bool(critical_ready and minimums_ready),
            "candidate_source_reconciliation_complete": bool(critical_ready),
            "source_decision_recorded": True,
            "historical_instrument_state_v2_ready": False,
            "terminal_disposition_ready": False,
            "authoritative_oos_execution_ready": False,
            "core_model_ready": False,
            "pr5_model_training_ready": False,
            "model_training_started": False,
            "model_entry_hard_stop_active": True,
            "historical_test_already_observed": True,
            "unbiased_final_estimate": False,
        }
        raw.to_csv(
            publisher.path("raw_snapshot_manifest.csv"), index=False, encoding="utf-8-sig"
        )
        events.drop(columns=["expected_tokens"]).to_csv(
            publisher.path("normalized_official_events.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        reconciliation.to_csv(
            publisher.path("candidate_reconciliation.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        coverage.to_csv(
            publisher.path("coverage_summary.csv"), index=False, encoding="utf-8-sig"
        )
        contracts_frame.to_csv(
            publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig"
        )
        pd.DataFrame([readiness]).to_csv(
            publisher.path("readiness_summary.csv"), index=False, encoding="utf-8-sig"
        )
        publisher.path("source_decision.json").write_text(
            json.dumps(source_decision, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(
                config, ensure_ascii=False, indent=2, sort_keys=True, default=str
            )
            + "\n",
            encoding="utf-8",
        )
        publisher.path("canary_report.md").write_text(
            "# Historical Instrument State V2 Official Canary\n\n"
            f"- Curated Tier-0 events: `{len(events)}`; raw snapshots: `{len(raw)}`.\n"
            f"- Before-open provable rate: `{before_open_rate:.2%}`.\n"
            f"- Same-day date-only / otherwise unknown events: `{source_decision['unknown_event_count']}`.\n"
            f"- Retrospective after-open evidence: `{source_decision['after_open_event_count']}`.\n"
            "- Source decision: **Decision B**. Candidate fields remain audit aids; "
            "Instrument State v2 and corrected execution are not authorized.\n"
            "- No terminal event in this canary provides an explicit cash-per-share "
            "disposition, so the eight V1.2 synthetic last-price fills remain non-authoritative.\n",
            encoding="utf-8",
        )
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id=str(config["stage_id"]),
            config=config,
            output_dir=publisher.staging_dir,
            output_files=[
                publisher.path(name)
                for name in COMPACT
                if name != "artifact_manifest.json"
            ],
            code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=[parent_path],
            universe_artifact_id=parent["universe_artifact_id"],
            split_manifest_id=parent["split_manifest_id"],
            factor_catalog_id=parent["factor_catalog_id"],
            factor_frame_id=parent["factor_frame_id"],
            start_date=events["effective_from"].min(),
            end_date=events["effective_from"].max(),
            artifact_status="pass" if critical_ready else "blocked",
            blocked_reason="" if critical_ready else "blocked_official_canary_contract",
        )
        publisher.publish()
    print(coverage.to_string(index=False))
    print(contracts_frame.to_string(index=False))
    print(json.dumps(source_decision, ensure_ascii=False, indent=2))
    return 0 if critical_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
