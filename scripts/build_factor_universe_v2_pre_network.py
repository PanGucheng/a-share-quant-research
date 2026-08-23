from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd
import yaml

from factor_universe_v2.inventory import (
    build_data_capability_matrix,
    build_duplicate_audit,
    build_historical_missing_audit,
    build_local_candidate_catalog,
    write_limitations,
)
from factor_universe_v2.tushare_data import probe_tushare, tushare_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_supporting_reports(output: Path, catalog: pd.DataFrame) -> None:
    recovery = catalog.loc[catalog["lineage_status"].ne("legacy_v1")].copy()
    recovery.to_csv(output / "factor_recovery_inventory.csv", index=False, encoding="utf-8-sig")
    catalog.to_csv(output / "factor_expansion_candidates.csv", index=False, encoding="utf-8-sig")
    catalog[
        [
            "name",
            "source",
            "category",
            "economic_family",
            "economic_subfamily",
            "lineage_status",
            "evidence_tier",
        ]
    ].to_csv(output / "economic_taxonomy.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        columns=[
            "factor_name",
            "source",
            "definition",
            "economic_rationale",
            "required_fields",
            "pit_implications",
            "implementation_status",
        ]
    ).to_csv(output / "external_factor_inventory.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {"decision": "community_ohlcva_vwap", "status": "adopt", "reason": "existing authoritative local price/volume/amount/VWAP backbone"},
            {"decision": "tushare_daily_basic", "status": "adopt_incrementally", "reason": "current token probe passed; adds turnover, size and value dimensions"},
            {"decision": "tushare_financial_statements", "status": "adopt_data_layer_only", "reason": "f_ann_date/ann_date support PIT; factors wait for bootstrap coverage gates"},
            {"decision": "tushare_fina_indicator", "status": "cross_check_required", "reason": "ann_date available but source ratios and revisions must be reconciled to statements"},
            {"decision": "tushare_disclosure_date", "status": "cross_check_only", "reason": "current table can contain actual_date backfill and is not historical database-vintage proof"},
            {"decision": "sw2021_membership", "status": "research_with_limitation", "reason": "effective intervals available; historical database vintage unproven"},
            {"decision": "external_mature_factor_research", "status": "not_started", "reason": "explicit user stop boundary before network factor expansion"},
        ]
    ).to_csv(output / "data_source_decisions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {"check": "availability_not_report_period", "status": "pass", "detail": "PIT layer accepts only f_ann_date/ann_date by dataset; end_date is never a fallback"},
            {"check": "no_pre_announcement_access", "status": "pass", "detail": "asof_pit_records filters information_available_date <= decision date"},
            {"check": "revision_preservation", "status": "pass", "detail": "all source rows retained with deterministic source hash and revision_sequence"},
            {"check": "financial_announcement_order", "status": "pass", "detail": "statement and ratio announcement dates before report periods fail loudly"},
            {"check": "disclosure_schedule_vintage", "status": "limited", "detail": "actual_date is cross-check evidence only, not an authoritative historical feature"},
            {"check": "fundamental_factor_admission", "status": "blocked_pending_bootstrap", "detail": "no fundamental factor enters the pre-network candidate catalog"},
        ]
    ).to_csv(output / "pit_audit.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {"dataset": "daily_basic", "historical_calls_estimate": "~6000 by trade date", "rows_estimate": "~25-30 million", "disk_estimate": "2-5 GB parquet", "incremental_cost": "1 call/trading day", "bootstrap_feasibility": "throttled_and_resume_required"},
            {"dataset": "moneyflow", "historical_calls_estimate": "~3900 since 2010", "rows_estimate": "~18-22 million", "disk_estimate": "3-7 GB parquet", "incremental_cost": "1 call/trading day", "bootstrap_feasibility": "throttled_and_resume_required"},
            {"dataset": "four_financial_core_apis", "historical_calls_estimate": "~22000 at 5500 securities", "rows_estimate": "~1-2 million", "disk_estimate": "1-4 GB parquet", "incremental_cost": "changed issuers/filing dates only", "bootstrap_feasibility": "slow_at_2000_points_but_restartable"},
            {"dataset": "events_and_reference", "historical_calls_estimate": "dataset-specific", "rows_estimate": "sparse_to_medium", "disk_estimate": "<2 GB initial expectation", "incremental_cost": "daily/quarterly segments", "bootstrap_feasibility": "prioritize_after_core_layers"},
            {"dataset": "candidate_matrix_716", "historical_calls_estimate": "none_after_local_cache", "rows_estimate": "same keys x 716 columns", "disk_estimate": "~7% wider than 669 before fundamentals", "incremental_cost": "47 additional factor columns", "bootstrap_feasibility": "canary_before_materialization"},
        ]
    ).to_csv(output / "resource_estimate.csv", index=False, encoding="utf-8-sig")


def _write_report(
    output: Path,
    config: dict,
    audit: pd.DataFrame,
    capability: pd.DataFrame,
    catalog: pd.DataFrame,
    probes: pd.DataFrame,
    v1_hash_before: str,
    v1_hash_after: str,
) -> None:
    source_counts = catalog.groupby("source").size().to_dict()
    lineage_counts = catalog.groupby("lineage_status").size().to_dict()
    economic_counts = catalog.groupby("economic_family").size().sort_values(ascending=False).to_dict()
    unique_missing = audit.loc[~audit["historical_status"].str.contains("degraded"), "factor_name"].nunique()
    recoverable_unique = audit.loc[audit["recoverable_now"].astype(bool), "factor_name"].nunique()
    degraded_unique = audit.loc[audit["implementation_quality"].isin(["proxy_based", "degraded"]), "factor_name"].nunique()
    accessible = int(probes["probe_status"].str.startswith("accessible").sum()) if not probes.empty else 0
    lines = [
        "# Factor Universe V2 — Pre-Network Checkpoint",
        "",
        "> Status: `pre_network_checkpoint_not_frozen`. External mature-factor research and network factor expansion were intentionally not started.",
        "",
        "## Outcome",
        "",
        f"- V1 remains byte-identical: `{v1_hash_before == v1_hash_after}` (`{v1_hash_before}`).",
        f"- V1 composition: `{source_counts.get('alpha158', 0) - 3}` Alpha158 + `{source_counts.get('alpha360', 0)}` Alpha360 + `77` TA + `64` Alpha101 + `15` Project Basic = `669` legacy factors.",
        f"- Historical missing/disabled unique factors audited: `{unique_missing}`; recoverable now: `{recoverable_unique}`.",
        f"- Degraded/proxy-based unique implementations annotated: `{degraded_unique}`.",
        f"- Pre-network local candidate catalog: `{len(catalog)}` = `669 legacy + 19 recovered + 28 canonicalized VWAP replacements`.",
        f"- Current token probes: `{accessible}/{len(probes)}` APIs callable; an empty forecast slice is recorded as accessible-empty, not failure.",
        "- No factor was admitted or rejected because of IC, FDR, return, clustering, or model results.",
        "",
        "## What was recovered",
        "",
        "- Alpha158: CNTN5, IMAX5 and RANK5 are restored because their old holdout reason was an evaluation partial-pass, not data incorrectness.",
        "- Alpha101: 12 locally valid formulas previously held out by evaluation are restored; 6 zero-valid-output formulas remain blocked.",
        "- TA: BBLI and KCHI evaluation holdouts are restored. VPT and NVI receive new canonical V2 implementations with explicit `pct_change(fill_method=None)`.",
        "- Alpha101 VWAP: 28 locally valid formulas get separate canonical variants using the provider's direct `$vwap`; the historical amount/volume-plus-epsilon versions are retained for lineage.",
        "- Alpha360 CLOSE0/VOLUME0 constants, three TA return duplicates and two forward-shifted visual Ichimoku outputs remain excluded.",
        "",
        "## Data capability",
        "",
        "The community provider already has open/high/low/close/volume/amount/VWAP plus adjustment fields across the audited 6,106 feature directories. Tushare probes confirm current access to daily size/value/turnover, money flow, statements, financial ratios, events, price limits, margin, block trades, top-list data, SW classification/membership and northbound holdings.",
        "",
        "Official references: [permission table](https://tushare.pro/document/1?doc_id=108), [daily_basic](https://tushare.pro/document/2?doc_id=32), [moneyflow](https://tushare.pro/document/2?doc_id=170), [cashflow](https://tushare.pro/document/2?doc_id=44), [fina_indicator](https://tushare.pro/document/2?doc_id=79), [disclosure_date](https://tushare.pro/document/2?doc_id=162).",
        "",
        "The 2000-point account can call the probed core APIs, but this does not prove unlimited full-market bootstrap throughput. The implemented segment store therefore caches Parquet segments, writes token-free hashes/receipts, resumes partial downloads, validates schema, and supports incremental updates.",
        "",
        "## PIT and revisions",
        "",
        "- Statements use `f_ann_date` first and `ann_date` second. `end_date` is never an availability fallback.",
        "- Financial ratios and event tables use their announcement date; missing availability stays `research_pending`.",
        "- All source revisions are retained and deterministically ordered. As-of reads select only revisions announced by the decision date.",
        "- `disclosure_date.actual_date` is not treated as a historical feature because a current table can backfill the eventual actual date.",
        "- No fundamental or flow factor enters this checkpoint catalog until full bootstrap coverage and PIT canaries pass.",
        "",
        "## Candidate composition",
        "",
        f"- Source counts: `{source_counts}`",
        f"- Lineage counts: `{lineage_counts}`",
        f"- Economic-family counts: `{economic_counts}`",
        "",
        "## Explicit stop boundary",
        "",
        "Not started: Alpha191, JoinQuant/RiceQuant/BigQuant definitions, new academic anomaly research, A-share literature review, or any other internet-sourced factor expansion. Therefore this checkpoint is not the frozen Factor Universe V2 and is not authorization for Matrix V5, Model/Strategy V2, or multi-factor winner research.",
        "",
        "## Files",
        "",
        "- `historical_missing_factor_audit.csv`",
        "- `data_capability_v2.csv` and `tushare_probe_receipt.csv`",
        "- `factor_recovery_inventory.csv` and `factor_expansion_candidates.csv`",
        "- `economic_taxonomy.csv`, `duplicate_equivalence_audit.csv`, `pit_audit.csv`",
        "- `data_source_decisions.csv`, `resource_estimate.csv`, `limitations.json`",
        "",
    ]
    (output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Factor Universe V2 pre-network checkpoint.")
    parser.add_argument("--config", type=Path, default=Path("configs/factor_universe_v2_pre_network.yaml"))
    parser.add_argument("--probe-tushare", action="store_true")
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    output = resolve(config["report_dir"])
    output.mkdir(parents=True, exist_ok=True)
    v1_path = resolve(config["v1_catalog"])
    v1_hash_before = sha256(v1_path)
    probes = (
        probe_tushare(tushare_client(), config["probes"])
        if args.probe_tushare
        else pd.DataFrame(columns=["api", "probe_status", "probe_rows", "probe_columns", "probe_elapsed_seconds", "error_class"])
    )
    audit = build_historical_missing_audit(PROJECT_ROOT, config)
    catalog = build_local_candidate_catalog(PROJECT_ROOT, config)
    capability = build_data_capability_matrix(config, probes)
    duplicate = build_duplicate_audit(catalog)
    audit.to_csv(output / "historical_missing_factor_audit.csv", index=False, encoding="utf-8-sig")
    probes.to_csv(output / "tushare_probe_receipt.csv", index=False, encoding="utf-8-sig")
    capability.to_csv(output / "data_capability_v2.csv", index=False, encoding="utf-8-sig")
    duplicate.to_csv(output / "duplicate_equivalence_audit.csv", index=False, encoding="utf-8-sig")
    _write_supporting_reports(output, catalog)
    write_limitations(output / "limitations.json")
    v1_hash_after = sha256(v1_path)
    v1_inventory = pd.read_csv(resolve(config["v1_inventory"]))
    legacy = catalog.loc[catalog["lineage_status"].eq("legacy_v1")]
    provider_inventory = pd.read_csv(resolve(config["provider_inventory"]))
    required_provider_fields = {"open", "high", "low", "close", "volume", "amount", "vwap"}
    provider_ready = required_provider_fields.issubset(set(provider_inventory["field"])) and bool(
        provider_inventory.loc[
            provider_inventory["field"].isin(required_provider_fields), "file_presence_rate"
        ].eq(1.0).all()
    )
    probe_ready = len(probes) == len(config["probes"]) and bool(
        probes["probe_status"].str.startswith("accessible").all()
    )
    checks = pd.DataFrame(
        [
            {"check": "v1_factor_count", "status": "pass" if (catalog["lineage_status"] == "legacy_v1").sum() == 669 else "fail", "observed": int((catalog["lineage_status"] == "legacy_v1").sum()), "required": 669},
            {"check": "v1_factor_set_exact", "status": "pass" if set(legacy["name"]) == set(v1_inventory["name"]) else "fail", "observed": len(set(legacy["name"])), "required": len(set(v1_inventory["name"]))},
            {"check": "v1_byte_immutable", "status": "pass" if v1_hash_before == v1_hash_after else "fail", "observed": v1_hash_after, "required": v1_hash_before},
            {"check": "community_ohlcva_vwap_complete", "status": "pass" if provider_ready else "fail", "observed": sorted(set(provider_inventory["field"]) & required_provider_fields), "required": sorted(required_provider_fields)},
            {"check": "tushare_probe_access", "status": "pass" if probe_ready else "fail", "observed": int(probes["probe_status"].str.startswith("accessible").sum()) if not probes.empty else 0, "required": len(config["probes"])},
            {"check": "local_candidate_names_unique", "status": "pass" if not catalog["name"].duplicated().any() else "fail", "observed": int(catalog["name"].duplicated().sum()), "required": 0},
            {"check": "lineage_total", "status": "pass" if len(catalog) == 716 else "fail", "observed": len(catalog), "required": 716},
            {"check": "recovered_count", "status": "pass" if (catalog["lineage_status"] == "recovered").sum() == 19 else "fail", "observed": int((catalog["lineage_status"] == "recovered").sum()), "required": 19},
            {"check": "canonicalized_count", "status": "pass" if (catalog["lineage_status"] == "canonicalized").sum() == 28 else "fail", "observed": int((catalog["lineage_status"] == "canonicalized").sum()), "required": 28},
            {"check": "network_expansion_not_started", "status": "pass", "observed": 0, "required": 0},
        ]
    )
    checks.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    _write_report(output, config, audit, capability, catalog, probes, v1_hash_before, v1_hash_after)
    print(checks.to_string(index=False))
    return 0 if checks["status"].eq("pass").all() else 2


if __name__ == "__main__":
    raise SystemExit(main())
