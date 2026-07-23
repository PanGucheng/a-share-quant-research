from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.feature_matrix import canonical_hash  # noqa: E402
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    load_artifact_manifest,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


OUTPUTS = [
    "artifact_manifest.json",
    "sample_manifest.csv",
    "sample_summary.csv",
    "contract_status.csv",
    "sample_freeze_report.md",
    "resolved_config.json",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze deterministic Data Source Audit V2 sample.")
    parser.add_argument("--config", type=Path, default=Path("configs/data_source_audit_v2.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    rng = np.random.default_rng(int(config["seed"]))
    state = pd.read_parquet(resolve(config["instrument_state"]))
    state["datetime"] = pd.to_datetime(state["datetime"]).dt.normalize()
    unique = (
        state.sort_values("datetime")
        .drop_duplicates("instrument", keep="last")[
            ["instrument", "board", "list_date", "delist_date"]
        ]
        .copy()
    )
    reasons: dict[str, set[str]] = defaultdict(set)
    evidence: dict[str, set[str]] = defaultdict(set)

    def add(instruments, reason: str, source: str) -> None:
        for instrument in instruments:
            reasons[str(instrument)].add(reason)
            evidence[str(instrument)].add(source)

    # 60 fixed-seed stratified random instruments.
    random_selected = []
    for board in ["main", "chinext", "star"]:
        values = unique.loc[unique["board"].eq(board), "instrument"].to_numpy()
        count = min(20, len(values))
        random_selected.extend(rng.choice(values, size=count, replace=False).tolist())
    add(random_selected, "stratified_random", f"instrument_state_v1;seed={config['seed']}")

    # Explicit board/code-range coverage, including the audited 302 code change.
    board_coverage = []
    for board in ["main", "chinext", "star"]:
        board_coverage.extend(
            unique.loc[unique["board"].eq(board), "instrument"].sort_values().head(7).tolist()
        )
    board_coverage.append("SZ302132")
    add(board_coverage[:20], "board_and_code_change", "instrument_state_v1;SZ302132_board_audit")

    cache_rows = pd.read_csv(resolve(config["market_cache_artifacts"]))
    market_parts = []
    for row in cache_rows.itertuples(index=False):
        frame = pd.read_parquet(
            Path(row.path),
            columns=[
                "instrument",
                "datetime",
                "suspended",
                "valuation_stale_blocked",
                "factor",
            ],
        )
        market_parts.append(frame)
    market = pd.concat(market_parts, ignore_index=True)
    gap = (
        market.assign(
            gap=lambda frame: frame["suspended"].astype(bool)
            | frame["valuation_stale_blocked"].astype(bool)
        )
        .groupby("instrument", as_index=False)["gap"]
        .sum()
        .sort_values(["gap", "instrument"], ascending=[False, True])
        .head(20)
    )
    add(gap["instrument"], "suspension_or_missing_span", "market_cache_v2")

    lifecycle = unique.copy()
    lifecycle["list_date"] = pd.to_datetime(lifecycle["list_date"], errors="coerce")
    lifecycle["delist_date"] = pd.to_datetime(lifecycle["delist_date"], errors="coerce")
    lifecycle = lifecycle.sort_values(
        ["delist_date", "list_date"], ascending=[True, False], na_position="last"
    ).head(15)
    add(lifecycle["instrument"], "ipo_or_lifecycle_boundary", "provider_lifecycle")

    factor_events = (
        market.sort_values(["instrument", "datetime"])
        .assign(
            factor_change=lambda frame: frame.groupby("instrument")["factor"]
            .pct_change(fill_method=None)
            .abs()
            .gt(1e-6)
        )
        .groupby("instrument", as_index=False)["factor_change"]
        .sum()
        .sort_values(["factor_change", "instrument"], ascending=[False, True])
        .head(20)
    )
    add(factor_events["instrument"], "adjustment_event", "community_factor_change")

    # Probe candidates are not claimed historical ST events. The final audit
    # promotes only observed BaoStock boundaries and reports any shortfall.
    probe_pool = unique.loc[~unique["instrument"].isin(reasons)].copy()
    st_probe = rng.choice(
        probe_pool["instrument"].to_numpy(), size=min(25, len(probe_pool)), replace=False
    )
    add(st_probe, "historical_st_probe", "candidate_probe_pending_external_evidence")

    target = int(config["sample_size"])
    if len(reasons) < target:
        remaining = unique.loc[~unique["instrument"].isin(reasons), "instrument"].to_numpy()
        fill = rng.choice(remaining, size=target - len(reasons), replace=False)
        add(fill, "coverage_fill", f"instrument_state_v1;seed={config['seed']}")
    ordered = sorted(reasons)[:target]
    sample = unique.set_index("instrument").loc[ordered].reset_index()
    sample["selection_reason"] = sample["instrument"].map(
        lambda value: "|".join(sorted(reasons[value]))
    )
    sample["event_evidence"] = sample["instrument"].map(
        lambda value: "|".join(sorted(evidence[value]))
    )
    sample["seed"] = int(config["seed"])
    sample["sample_sha256"] = canonical_hash(
        sample[["instrument", "selection_reason", "event_evidence"]].to_dict("records")
    )
    summary = (
        sample.assign(reason=sample["selection_reason"].str.split("|"))
        .explode("reason")
        .groupby("reason", as_index=False)
        .agg(instrument_count=("instrument", "nunique"))
    )
    critical_ready = (
        len(sample) == target
        and sample["instrument"].nunique() == target
        and {"main", "chinext", "star"}.issubset(set(sample["board"]))
        and sample["event_evidence"].astype(str).str.len().gt(0).all()
    )
    contract = pd.DataFrame(
        [
            {"check_name": "sample_size", "status": "pass" if len(sample) == target else "blocked", "observed_value": len(sample), "required_value": target, "severity": "critical", "reason": ""},
            {"check_name": "duplicate_instrument_count", "status": "pass" if sample["instrument"].is_unique else "blocked", "observed_value": int(sample["instrument"].duplicated().sum()), "required_value": 0, "severity": "critical", "reason": ""},
            {"check_name": "board_strata_present", "status": "pass" if {"main", "chinext", "star"}.issubset(set(sample["board"])) else "blocked", "observed_value": "|".join(sorted(sample["board"].unique())), "required_value": "chinext|main|star", "severity": "critical", "reason": ""},
            {"check_name": "selection_evidence_present", "status": "pass" if sample["event_evidence"].astype(str).str.len().gt(0).all() else "blocked", "observed_value": int(sample["event_evidence"].astype(str).str.len().gt(0).sum()), "required_value": target, "severity": "critical", "reason": ""},
        ]
    )
    output_dir = resolve(config["sample_output"])
    parents = [
        resolve(config["instrument_state_manifest"]),
        resolve(config["market_cache_manifest"]),
        resolve(config["universe_manifest"]),
    ]
    state_manifest = load_artifact_manifest(parents[0])
    with StageOutputPublisher(output_dir, OUTPUTS) as publisher:
        sample.to_csv(publisher.path("sample_manifest.csv"), index=False, encoding="utf-8-sig")
        summary.to_csv(publisher.path("sample_summary.csv"), index=False, encoding="utf-8-sig")
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("sample_freeze_report.md").write_text(
            "# Data Source Audit V2 Sample Freeze\n\n"
            f"- Instruments: `{len(sample)}`\n"
            f"- Seed: `{config['seed']}`\n"
            f"- Sample SHA-256: `{sample['sample_sha256'].iloc[0]}`\n"
            "- ST probe candidates are not treated as verified ST events until external evidence is observed.\n",
            encoding="utf-8",
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="data_source_audit_sample_v2",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=[publisher.path(name) for name in OUTPUTS if name != "artifact_manifest.json"],
            code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=parents,
            universe_artifact_id=state_manifest["universe_artifact_id"],
            split_manifest_id=state_manifest["split_manifest_id"],
            start_date=config["start_date"],
            end_date=config["end_date"],
            artifact_status="pass" if critical_ready else "blocked",
            blocked_reason="" if critical_ready else "blocked_sample_freeze",
        )
        publisher.publish()
    print(summary.to_string(index=False))
    return 0 if critical_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
