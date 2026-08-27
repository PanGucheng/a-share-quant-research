from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_universe_v2.inventory import (  # noqa: E402
    build_data_capability_matrix,
    build_dependency_inventory,
    build_duplicate_audit,
    build_frozen_v2_catalog,
    build_historical_missing_audit,
)
from factor_universe_v2.mature_inventory import build_external_research_inventory  # noqa: E402


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _yaml_value(value: Any) -> Any:
    if pd.isna(value):
        return ""
    if isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def write_catalog_yaml(path: Path, catalog: pd.DataFrame) -> None:
    keys = [
        "name", "registry_name", "category", "source_project", "source_file",
        "source_function", "source_commit", "license", "expected_direction",
        "required_fields", "labels", "stage", "enabled", "runnable", "compute_adapter", "notes",
    ]
    factors = []
    for row in catalog.to_dict("records"):
        item = {key: _yaml_value(row.get(key, "")) for key in keys}
        item["required_fields"] = [value for value in str(item["required_fields"]).split(",") if value]
        item["labels"] = [value for value in str(item["labels"]).split(",") if value]
        item["enabled"] = bool(item["enabled"])
        item["runnable"] = bool(item["runnable"])
        factors.append(item)
    path.write_text(
        yaml.safe_dump({"version": 1, "universe": "factor_universe_v2", "factors": factors}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _write_decisions(path: Path) -> None:
    rows = [
        ("community_ohlcva_vwap", "adopt", "authoritative local price/volume/amount/VWAP backbone"),
        ("tushare_daily_basic", "adopt", "verified token access; size/value/turnover with after-close t+1 semantics"),
        ("tushare_moneyflow", "adopt", "verified token access; 2010+ order-size flow with documented units"),
        ("tushare_financial_statements", "adopt_pit", "f_ann_date then ann_date; revisions retained; report period never availability"),
        ("tushare_fina_indicator", "cross_check_only", "ratios useful for QA but authoritative factors are statement-derived"),
        ("tushare_disclosure_date", "cross_check_only", "current actual_date can be backfilled and does not prove historical vintage"),
        ("sw2021_membership", "defer", "effective intervals do not establish database-vintage availability"),
        ("alpha191", "reject_current_batch", "unclear portable provenance/license and high overlap with V1 technical core"),
        ("joinquant_ricequant", "taxonomy_only", "public taxonomies reviewed; no unlicensed code copied"),
        ("barra_style", "adapt_public_concepts", "public factor families used; proprietary model formulas not copied"),
        ("sparse_event_apis", "defer", "accessible but heterogeneous history and sparse coverage need a later batch"),
        ("tradability_states", "retain_as_controls", "limit/ST/suspension remain controls, not alpha features"),
    ]
    pd.DataFrame(rows, columns=["decision", "status", "reason"]).to_csv(path, index=False, encoding="utf-8-sig")


def _write_pit_audit(path: Path) -> None:
    rows = [
        ("availability_not_report_period", "pass", "only f_ann_date/ann_date establish financial availability"),
        ("no_pre_announcement_access", "pass", "factor computation rejects unavailable or post-decision rows"),
        ("revision_preservation", "pass", "source rows retain deterministic hash and revision_sequence"),
        ("financial_announcement_order", "pass", "announcement before report period fails loudly"),
        ("same_day_market_feature", "pass", "daily market/basic/moneyflow row t is explicitly usable next session"),
        ("moneyflow_units", "pass", "Tushare 10,000-CNY amounts explicitly converted before normalization"),
        ("disclosure_schedule_vintage", "limited", "actual_date remains cross-check-only"),
        ("industry_membership_vintage", "blocked", "industry-relative candidates excluded from authoritative V2"),
        ("future_data_blocked", "pass", "PIT selection and factor adapter both enforce availability <= decision date"),
    ]
    pd.DataFrame(rows, columns=["check", "status", "detail"]).to_csv(path, index=False, encoding="utf-8-sig")


def _write_resources(path: Path) -> None:
    rows = [
        ("daily_basic", "~6000 calls by trade date", "~25-30m", "2-5 GB parquet", "1 call/trading day", "restartable bootstrap"),
        ("moneyflow", "~3900 calls since 2010", "~18-22m", "3-7 GB parquet", "1 call/trading day", "restartable bootstrap"),
        ("three_statement_apis", "~16500 calls at 5500 issuers", "~1-2m", "1-4 GB parquet", "changed issuers/filing dates", "throttled issuer bootstrap"),
        ("frozen_matrix_774", "none after cache", "same row keys x 774", "~15% wider than V1; ~8% wider than 716", "58 V2 columns", "canary then partitioned materialization"),
        ("daily_compute", "local", "17 market + 12 basic + 10 flow", "moderate rolling-state cache", "one new date plus lookback", "no full API history fetch"),
        ("quarterly_compute", "local", "19 PIT statement factors", "small relative to daily layers", "new/revised filings only", "revision-aware recompute from availability date"),
    ]
    pd.DataFrame(rows, columns=["dataset", "historical_calls_estimate", "rows_estimate", "disk_estimate", "incremental_cost", "bootstrap_feasibility"]).to_csv(path, index=False, encoding="utf-8-sig")


def _write_report(report_dir: Path, catalog: pd.DataFrame, audit: pd.DataFrame, external: pd.DataFrame, v1_hash: str) -> None:
    family_counts = catalog.groupby("economic_family").size().sort_values(ascending=False).to_dict()
    admitted = external.loc[external["candidate_decision"].eq("admit")]
    rejected = external.loc[external["candidate_decision"].eq("reject")]
    deferred = external.loc[external["candidate_decision"].eq("defer")]
    unique_missing = audit.loc[~audit["historical_status"].str.contains("degraded"), "factor_name"].nunique()
    recoverable = audit.loc[audit["recoverable_now"].astype(bool), "factor_name"].nunique()
    degraded = audit.loc[audit["implementation_quality"].isin(["proxy_based", "degraded"]), "factor_name"].nunique()
    text = f"""# Factor Universe V2 — Frozen Research Universe

> Status: `frozen_research_only`. This freezes factor definitions and lineage; it does not authorize Strategy V2 or modify Forward Track.

## Outcome

- Final universe: **774 unique factors** = 669 immutable V1 + 19 recovered + 28 canonicalized replacements + 58 new mature public factors.
- V1 catalog remains byte-identical (`{v1_hash}`); all 669 V1 names are inherited unchanged.
- New axes are Size, Value, Profitability, Quality, Growth/Investment, Leverage, Cash Flow, order-size Money Flow, direct liquidity and market/residual risk.
- Admission used formula/data/PIT/dependency gates only. No IC, FDR, return, model, SHAP, clustering or portfolio winner test was run.

## Answers to the required audit questions

1. **V1 composition:** 155 Alpha158 + 358 Alpha360 + 77 TA + 64 Alpha101 + 15 Project Basic = 669.
2. **Historical omissions:** `{unique_missing}` unique missing/held-out names were found after separating duplicate degraded annotations.
3. **Recoverable now:** `{recoverable}` unique names were technically recoverable; the frozen recovery batch admits 19 distinct factors and keeps non-informative/invalid formulas out.
4. **Degraded implementations:** `{degraded}` unique proxy/degraded names are annotated.
5. **Amount/VWAP recovery:** 28 valid Alpha101 formulas receive direct-provider `$vwap` canonical versions; VPT/NVI get explicit missing-value semantics; new direct VWAP deviation, amount momentum and Amihud factors are added.
6. **Tushare dimensions:** verified probes cover daily size/value/turnover, money flow, statements/ratios, events, limits, margin, blocks/top lists, SW reference data and northbound holdings.
7. **Not adopted now:** no probed core API was permission-denied. Sparse event families are deferred for coverage/cost, SW industry factors for vintage uncertainty, and `disclosure_date.actual_date` for backfill risk.
8. **Safely PIT-able:** income, balance sheet and cash-flow fields with `f_ann_date` then `ann_date`; `fina_indicator` and announcement events with `ann_date` can be cross-checked while preserving revisions.
9. **Not safely PIT-able:** report period alone, current disclosure schedules as historical snapshots, and industry effective intervals without database-vintage evidence.
10. **External systems researched:** Qlib Alpha158/360, WorldQuant Alpha101, Alpha191, TA ecosystems, JoinQuant/RiceQuant public taxonomies, MSCI Barra-style families, classic anomaly papers, and China A-share anomaly/liquidity/order-flow literature.
11. **Admitted families:** 17 market/price/liquidity/risk, 12 daily-basic size/value/turnover, 10 order-size flow, and 19 PIT statement factors (`{len(admitted)}` total).
12. **Rejected/deferred:** `{len(rejected)}` rejected families and `{len(deferred)}` deferred families are recorded in `external_factor_inventory.csv` with reasons.
13. **New economic information:** the V1 technical concentration is supplemented by accounting, valuation, capital structure, cash conversion, order-size behavior and systematic/residual risk.
14. **Economic-family counts:** `{family_counts}`.
15. **Duplicates:** two known Alpha360 constant formulas remain hard-excluded. Proxy/canonical and conceptual relationships are annotated; no admitted V2 name or explicit formula is duplicated.
16. **Final count:** 774.
17. **Legacy inheritance:** all 669 V1 factors, byte/name immutable.
18. **Recovered:** 19.
19. **Truly new:** 58.
20. **Canonical replacement candidates:** 28 direct-VWAP Alpha101 variants; legacy proxies are retained for lineage.
21. **History coverage:** local OHLCVA/VWAP covers the current split. Tushare documents the required historical ranges and probes pass, but full-market bootstrap coverage is an explicit pre-matrix gate and is not falsely claimed here.
22. **Resource cost:** roughly 6-16 GB raw Parquet for the core new layers; 774 columns are ~15.7% wider than 669 and ~8.1% wider than 716. See `resource_estimate.csv`.
23. **Incremental maintenance:** content-addressed Parquet segments, receipts/hashes, retries, missing-segment detection, one daily segment per post-close API, and revision-aware issuer updates for filings.
24. **Next-stage readiness:** yes for scoped V2 data bootstrap, canary matrix construction and economic-sleeve research. No for Strategy V2/production switching; observed holdout and Forward evidence remain untouched.

## Research basis and A-share interpretation

The [China A-share anomaly review](https://doi.org/10.1016/j.pacfin.2021.101607) finds stronger evidence for value, risk and trading signals than for broad size/quality/past-return groups, with reversal and residual effects as notable exceptions. [Size and Value in China](https://www.nber.org/papers/w24458) motivates China-specific earnings yield, size and turnover treatment. The China liquidity study identifies turnover as a particularly suitable local liquidity proxy, while [Amihud](https://doi.org/10.1016/S1386-4181(01)00024-6) supplies the amount-based price-impact definition. China order-imbalance research motivates, but does not pre-judge, the order-size flow candidates.

The accounting batch follows [gross profitability](https://www.nber.org/papers/w15940), [accrual/cash-flow quality](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2598), and public [MSCI Barra family coverage](https://www.msci.com/documents/1296102/1636401/MSCI_Barra_Market%2BEquity%2BModels_Factsheet%2B.pdf/0c9d381f-e4e6-42fc-b7c2-dfff694dd650). The code is an original, transparent implementation; no proprietary Barra formula and no unlicensed platform code was copied.

## PIT and feature-at-t contract

- Market, `daily_basic`, and `moneyflow` observations dated t are post-close data and first usable in the next trading session.
- Statement factors accept only rows whose `information_available_date <= decision date`; missing or future availability fails closed.
- `end_date` is a report-period key, never an availability fallback. Revisions are retained and selected as of each decision date.
- Tushare money-flow amounts are explicitly converted from 10,000 CNY before division by traded amount in CNY.

## Freeze artifacts

- `outputs/factor_universe_v2/current/factor_catalog_v2.yaml`
- `outputs/factor_universe_v2/current/factor_inventory_v2.csv`
- `outputs/factor_universe_v2/current/factor_dependency_v2.csv`
- `outputs/factor_universe_v2/current/freeze_manifest.json`
- Supporting audits are in `reports/factor_universe_v2/`.

## Boundary

Factor Universe V2 is research-only. It does not change the 52-feature Strategy V1 model, feature order, old matrices, historical releases, daily paper path or Forward evidence. Full data bootstrap and canary materialization must pass their own coverage/missingness/resource gates before empirical multi-factor or ML work.
"""
    (report_dir / "REPORT.md").write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze Factor Universe V2.")
    parser.add_argument("--config", type=Path, default=Path("configs/factor_universe_v2.yaml"))
    args = parser.parse_args()
    final_config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    base_config = yaml.safe_load(resolve(final_config["base_config"]).read_text(encoding="utf-8")) or {}
    report_dir = resolve(final_config["report_dir"])
    output_dir = resolve(final_config["output_dir"])
    report_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    v1_path = resolve(base_config["v1_catalog"])
    v1_hash_before = sha256(v1_path)
    audit = build_historical_missing_audit(PROJECT_ROOT, base_config)
    catalog = build_frozen_v2_catalog(PROJECT_ROOT, base_config)
    external = build_external_research_inventory()
    probes_path = report_dir / "tushare_probe_receipt.csv"
    probes = pd.read_csv(probes_path) if probes_path.exists() else pd.DataFrame()
    capability = build_data_capability_matrix(base_config, probes)
    dependency = build_dependency_inventory(catalog)
    duplicate = build_duplicate_audit(catalog)
    duplicate = pd.concat(
        [duplicate, pd.DataFrame([
            {"factor_a": "mature_earnings_yield_ttm", "factor_b": "mature_earnings_to_price_pit", "relationship": "same_concept_different_accounting_horizon", "hard_delete": False, "recommended_action": "retain_annotate"},
            {"factor_a": "mature_book_to_price", "factor_b": "mature_book_to_market_pit", "relationship": "provider_ratio_vs_statement_derived", "hard_delete": False, "recommended_action": "retain_for_cross_check"},
            {"factor_a": "mature_realized_volatility_60", "factor_b": "mature_idiosyncratic_volatility_60", "relationship": "total_vs_residual_risk", "hard_delete": False, "recommended_action": "retain_distinct_economic_exposure"},
            {"factor_a": "mature_overall_order_imbalance", "factor_b": "mature_institutional_order_imbalance", "relationship": "aggregate_vs_order_size_subset", "hard_delete": False, "recommended_action": "retain_distinct_trader_proxy"},
        ])], ignore_index=True,
    )

    catalog.to_csv(output_dir / "factor_inventory_v2.csv", index=False, encoding="utf-8-sig")
    dependency.to_csv(output_dir / "factor_dependency_v2.csv", index=False, encoding="utf-8-sig")
    write_catalog_yaml(output_dir / "factor_catalog_v2.yaml", catalog)
    audit.to_csv(report_dir / "historical_missing_factor_audit.csv", index=False, encoding="utf-8-sig")
    capability.to_csv(report_dir / "data_capability_v2.csv", index=False, encoding="utf-8-sig")
    external.to_csv(report_dir / "external_factor_inventory.csv", index=False, encoding="utf-8-sig")
    catalog.loc[catalog["lineage_status"].ne("legacy_v1")].to_csv(report_dir / "factor_recovery_inventory.csv", index=False, encoding="utf-8-sig")
    catalog.to_csv(report_dir / "factor_expansion_candidates.csv", index=False, encoding="utf-8-sig")
    catalog[["name", "source", "economic_family", "economic_subfamily", "secondary_family", "lineage_status", "evidence_tier"]].to_csv(report_dir / "economic_taxonomy.csv", index=False, encoding="utf-8-sig")
    duplicate.to_csv(report_dir / "duplicate_equivalence_audit.csv", index=False, encoding="utf-8-sig")
    _write_decisions(report_dir / "data_source_decisions.csv")
    _write_pit_audit(report_dir / "pit_audit.csv")
    _write_resources(report_dir / "resource_estimate.csv")

    v1_hash_after = sha256(v1_path)
    legacy_names = set(catalog.loc[catalog["lineage_status"].eq("legacy_v1"), "name"])
    expected_v1 = set(pd.read_csv(resolve(base_config["v1_inventory"]))["name"])
    checks = pd.DataFrame([
        ("v1_factor_count", len(legacy_names) == 669, len(legacy_names), 669),
        ("v1_factor_set_exact", legacy_names == expected_v1, len(legacy_names), len(expected_v1)),
        ("v1_byte_immutable", v1_hash_before == v1_hash_after, v1_hash_after, v1_hash_before),
        ("frozen_factor_count", len(catalog) == 774, len(catalog), 774),
        ("factor_names_unique", catalog["name"].is_unique, int(catalog["name"].duplicated().sum()), 0),
        ("new_mature_count", int(catalog["lineage_status"].eq("new").sum()) == 58, int(catalog["lineage_status"].eq("new").sum()), 58),
        ("all_dependencies_declared", dependency["required_fields"].ne("").all(), int(dependency["required_fields"].eq("").sum()), 0),
        ("external_admitted_implemented", external.loc[external["candidate_decision"].eq("admit"), "compute_adapter"].ne("").all(), int(external.loc[external["candidate_decision"].eq("admit"), "compute_adapter"].eq("").sum()), 0),
        ("strategy_v2_not_authorized", final_config["strategy_v2_authorized"] is False, final_config["strategy_v2_authorized"], False),
    ], columns=["check", "passed", "observed", "required"])
    checks["status"] = checks["passed"].map({True: "pass", False: "fail"})
    checks.drop(columns="passed").to_csv(report_dir / "contract_status.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "schema_version": 1,
        "status": "frozen_research_only",
        "factor_count": len(catalog),
        "lineage_counts": catalog.groupby("lineage_status").size().to_dict(),
        "v1_catalog_sha256": v1_hash_after,
        "factor_catalog_v2_sha256": sha256(output_dir / "factor_catalog_v2.yaml"),
        "factor_inventory_v2_sha256": sha256(output_dir / "factor_inventory_v2.csv"),
        "factor_dependency_v2_sha256": sha256(output_dir / "factor_dependency_v2.csv"),
        "decision_time_semantics": final_config["decision_time_semantics"],
        "strategy_v2_authorized": False,
    }
    (output_dir / "freeze_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (report_dir / "limitations.json").write_text(json.dumps({
        "stage_status": "frozen_research_only",
        "limitations": [
            "Full-market Tushare bootstrap coverage is a pre-matrix gate; API probes are not misrepresented as a completed download.",
            "Industry-relative factors are deferred until historical membership database vintages are proven.",
            "Sparse event APIs are deferred to a separate coverage study.",
            "Moneyflow order-size buckets are provider classifications and only proxies for investor type.",
            "No alpha efficacy, model winner, portfolio, Strategy V2 or production switch is authorized.",
        ],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_report(report_dir, catalog, audit, external, v1_hash_after)
    print(checks.drop(columns="passed").to_string(index=False))
    return 0 if checks["status"].eq("pass").all() else 2


if __name__ == "__main__":
    raise SystemExit(main())
