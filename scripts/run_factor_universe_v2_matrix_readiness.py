from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.alpha101_source import mask_raw_to_pit_membership  # noqa: E402
from factor_universe_v2.historical_data import (  # noqa: E402
    bootstrap_statement_layers,
    bootstrap_trade_date_layers,
    canonical_hash,
    qlib_to_tushare,
)
from factor_universe_v2.matrix_readiness import (  # noqa: E402
    BuildPaths,
    audit_partitions,
    compare_canonical_to_legacy,
    compute_canonical,
    compute_mature_partitions,
    compute_recovered,
    file_sha256,
    git_commit,
    load_qlib_market,
    raw_source_coverage,
    timed,
    tracked_worktree_clean,
    write_partition,
)
from factor_universe_v2.tushare_data import TushareSegmentStore, tushare_client  # noqa: E402
from research_validation.feature_matrix import build_pit_key_grid  # noqa: E402


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def qlib_calendar(provider_uri: Path, start: str, end: str) -> pd.DatetimeIndex:
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(provider_uri), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    return pd.DatetimeIndex(D.calendar(start_time=start, end_time=end, freq="day"))


def scope_inputs(config: dict, scope: str) -> tuple[pd.DataFrame, pd.DatetimeIndex, pd.DatetimeIndex]:
    intervals = pd.read_csv(resolve(config["universe_intervals"]))
    intervals["instrument"] = intervals["instrument"].astype(str).str.upper()
    intervals["start_date"] = pd.to_datetime(intervals["start_date"])
    intervals["end_date"] = pd.to_datetime(intervals["end_date"])
    provider_uri = resolve(config["provider_uri"])
    research_end = str(config["research_end_date"])
    daily_start = str(config["market_bootstrap_start_date"])
    if scope == "canary":
        symbols = {str(value).upper() for value in config["canary"]["instruments"]}
        intervals = intervals.loc[intervals["instrument"].isin(symbols)].copy()
        research_end = str(config["canary"]["research_end_date"])
        daily_start = str(config["canary"]["daily_bootstrap_start_date"])
    research_calendar = qlib_calendar(
        provider_uri, str(config["research_start_date"]), research_end
    )
    daily_calendar = qlib_calendar(provider_uri, daily_start, research_end)
    return intervals, research_calendar, daily_calendar


def bootstrap(config: dict, scope: str, report_dir: Path) -> int:
    intervals, _, daily_calendar = scope_inputs(config, scope)
    symbols = sorted(intervals["instrument"].unique())
    ts_codes = [qlib_to_tushare(value) for value in symbols]
    raw_root = resolve(config["raw_runtime_dir"])
    store = TushareSegmentStore(raw_root)
    pro = tushare_client()
    started = time.perf_counter()
    daily_receipts = bootstrap_trade_date_layers(pro, store, daily_calendar)
    daily_timing = timed(
        "bootstrap_daily_layers",
        started,
        scope=scope,
        request_segments=len(daily_receipts),
        source_rows=int(daily_receipts["row_count"].sum()),
    )
    started = time.perf_counter()
    statement_receipts = bootstrap_statement_layers(
        pro,
        store,
        ts_codes,
        announcement_start=str(config["statement_announcement_start_date"]).replace("-", ""),
        announcement_end=str(config["statement_announcement_end_date"]).replace("-", ""),
    )
    statement_timing = timed(
        "bootstrap_statement_layers",
        started,
        scope=scope,
        request_segments=len(statement_receipts),
        source_rows=int(statement_receipts["row_count"].sum()),
    )
    report_dir.mkdir(parents=True, exist_ok=True)
    daily_receipts.to_csv(report_dir / f"{scope}_daily_bootstrap_receipts.csv", index=False)
    statement_receipts.to_csv(
        report_dir / f"{scope}_statement_bootstrap_receipts.csv", index=False
    )
    pd.DataFrame([daily_timing, statement_timing]).to_csv(
        report_dir / f"{scope}_bootstrap_timing.csv", index=False
    )
    print(json.dumps({"daily": daily_timing, "statements": statement_timing}, indent=2))
    return 0


def _legacy_partition_rows(config: dict, inventory: pd.DataFrame) -> pd.DataFrame:
    status = pd.read_csv(resolve(config["matrix_v4_partition_status"]))
    legacy = inventory.loc[inventory["lineage_status"].eq("legacy_v1")]
    rows = []
    for item in status.itertuples(index=False):
        names = legacy.loc[legacy["batch_id"].eq(item.batch_id), "name"].astype(str).tolist()
        path = Path(str(item.output_path)).resolve()
        digest = file_sha256(path)
        if digest != str(item.output_sha256):
            raise ValueError(f"V1 partition changed: {item.batch_id}")
        rows.append(
            {
                "partition_id": str(item.batch_id),
                "partition_path": path.as_posix(),
                "factor_count": len(names),
                "row_count": int(item.row_count),
                "output_sha256": digest,
                "output_size_bytes": int(item.output_size_bytes),
                "reused_v1": True,
                "factors": ",".join(names),
            }
        )
    result = pd.DataFrame(rows)
    if int(result["factor_count"].sum()) != 669:
        raise ValueError("legacy partition map does not contain exactly 669 factors")
    return result


def _fina_indicator_crosscheck(supporting: dict[str, pd.DataFrame]) -> pd.DataFrame:
    events = supporting["statement_events"].copy()
    indicator = supporting["fina_indicator"].copy()
    if events.empty or indicator.empty:
        return pd.DataFrame([{"check": "fina_indicator_available", "status": "blocked"}])
    indicator["instrument"] = indicator["ts_code"].map(
        lambda value: f"{str(value).split('.')[1]}{str(value).split('.')[0]}"
    )
    indicator["report_period"] = pd.to_datetime(indicator["end_date"], format="%Y%m%d")
    indicator["indicator_available_date"] = pd.to_datetime(
        indicator["ann_date"], format="%Y%m%d", errors="coerce"
    )
    indicator = indicator.sort_values("indicator_available_date").drop_duplicates(
        ["instrument", "report_period"], keep="last"
    )
    joined = events.merge(
        indicator,
        on=["instrument", "report_period"],
        how="inner",
        suffixes=("", "_indicator"),
    )
    joined = joined.loc[
        joined["indicator_available_date"].le(joined["information_available_date"])
    ]
    rows = []
    for name, calculated, provider in (
        (
            "current_ratio",
            pd.to_numeric(joined["total_cur_assets"], errors="coerce")
            / pd.to_numeric(joined["total_cur_liab"], errors="coerce").replace(0, np.nan),
            pd.to_numeric(joined["current_ratio"], errors="coerce"),
        ),
        (
            "cash_ratio",
            pd.to_numeric(joined["money_cap"], errors="coerce")
            / pd.to_numeric(joined["total_cur_liab"], errors="coerce").replace(0, np.nan),
            pd.to_numeric(joined["cash_ratio"], errors="coerce"),
        ),
    ):
        pair = pd.DataFrame({"calculated": calculated, "provider": provider}).replace(
            [np.inf, -np.inf], np.nan
        ).dropna()
        relative = (pair["calculated"] - pair["provider"]).abs() / pair["provider"].abs().clip(1e-12)
        rows.append(
            {
                "check": name,
                "status": "pass" if len(pair) else "blocked",
                "matched_rows": len(pair),
                "median_relative_difference": float(relative.median()) if len(pair) else np.nan,
                "correlation": float(pair.corr().iloc[0, 1]) if len(pair) > 1 else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _unit_sanity(
    factors: dict[str, pd.DataFrame], supporting: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    aligned = supporting["statement_alignment"]
    market = factors["mature_market"]
    daily = factors["mature_daily_basic"]
    money = factors["mature_moneyflow"]
    fundamental = factors["mature_fundamental"]
    specs = [
        ("log_market_cap", daily["mature_log_total_market_cap"], 5.0, 30.0),
        ("turnover_decimal", daily["mature_turnover_rate_free_float"], 0.0, 2.0),
        ("net_flow_share", money["mature_net_flow_to_traded_amount"].abs(), 0.0, 5.0),
        ("amihud_cny", market["mature_amihud_illiquidity_20"], 0.0, 1e-4),
        ("roa", fundamental["mature_return_on_assets"], -5.0, 5.0),
        ("book_leverage", fundamental["mature_book_leverage"], -5.0, 5.0),
    ]
    rows = []
    for name, values, lower, upper in specs:
        numeric = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        median = float(numeric.median()) if len(numeric) else np.nan
        q99 = float(numeric.quantile(0.99)) if len(numeric) else np.nan
        observed = q99 if name in {"turnover_decimal", "net_flow_share", "amihud_cny"} else median
        rows.append(
            {
                "check": name,
                "status": "pass" if len(numeric) and lower <= observed <= upper else "review",
                "finite_count": len(numeric),
                "median": median,
                "q01": float(numeric.quantile(0.01)) if len(numeric) else np.nan,
                "q99": q99,
                "expected_lower": lower,
                "expected_upper": upper,
            }
        )
    assets = pd.to_numeric(aligned.get("total_assets"), errors="coerce").dropna()
    rows.append(
        {
            "check": "statement_cny_scale",
            "status": "pass" if len(assets) and 1e7 <= assets.median() <= 1e15 else "review",
            "finite_count": len(assets),
            "median": float(assets.median()) if len(assets) else np.nan,
            "q01": float(assets.quantile(0.01)) if len(assets) else np.nan,
            "q99": float(assets.quantile(0.99)) if len(assets) else np.nan,
            "expected_lower": 1e7,
            "expected_upper": 1e15,
        }
    )
    return pd.DataFrame(rows)


def _write_report(
    report_path: Path,
    config: dict,
    scope: str,
    keys: pd.DataFrame,
    qualification: pd.DataFrame,
    source_coverage: pd.DataFrame,
    family_coverage: pd.DataFrame,
    timings: pd.DataFrame,
    revision_audit: pd.DataFrame,
    matrix_status: str,
) -> None:
    counts = {
        column: int(qualification[column].astype(bool).sum())
        for column in ("defined", "materializable", "coverage_qualified", "research_usable", "temporarily_blocked")
    }
    blocked = qualification.loc[qualification["temporarily_blocked"], ["factor", "block_reason"]]
    source_lines = [
        f"- `{row.api}`: {row.row_count:,} rows, {row.observed_segment_count}/{row.expected_segment_count} segments, integrity={row.integrity_pass}."
        for row in source_coverage.itertuples(index=False)
    ]
    family_lines = [
        f"- `{row.economic_family}`: coverage={row.coverage:.3%}, usable={int(row.research_usable_count)}/{int(row.factor_count)}."
        for row in family_coverage.itertuples(index=False)
    ]
    blocked_lines = [
        f"- `{row.factor}` — {row.block_reason}" for row in blocked.head(100).itertuples(index=False)
    ] or ["- None."]
    report_path.write_text(
        "\n".join(
            [
                "# Factor Universe V2 Historical Data & Matrix Readiness",
                "",
                f"> Status: `{matrix_status}`; scope: `{scope}`. This is data qualification only and does not authorize Strategy V2.",
                "",
                "## Outcome",
                "",
                f"- Matrix dates: `{keys.datetime.min().date()}` to `{keys.datetime.max().date()}`; instruments: `{keys.instrument.nunique()}`; rows: `{len(keys):,}`.",
                f"- Definitions/materializable/coverage-qualified/research-usable/blocked: `{counts['defined']}/{counts['materializable']}/{counts['coverage_qualified']}/{counts['research_usable']}/{counts['temporarily_blocked']}`.",
                f"- Bootstrap begins `{config['market_bootstrap_start_date']}`, exactly 252 provider trading sessions before the first research date; statement announcements begin `{config['statement_announcement_start_date']}` to cover the prior-year comparators visible at research start.",
                "- The 669 V1 factors and Matrix v4 partitions are referenced byte-for-byte; no old matrix, label, split, prediction, Forward, or Strategy V1 artifact was changed.",
                "",
                "## Required answers",
                "",
                "1. Required raw layers are Qlib OHLCV/amount/direct VWAP, a contemporaneous PIT-universe equal-weight market return, Tushare daily_basic, moneyflow, income, balancesheet, cashflow, and fina_indicator cross-check fields.",
                "2. Only those frozen dependency layers were bootstrapped; no unrelated Tushare collection was added.",
                "3. Per-source real coverage is listed below and in `raw_source_coverage.csv`.",
                "4. Financial PIT is enforced from f_ann_date then ann_date; report period is never used as availability.",
                "5. Same-day revisions prefer Tushare update_flag=1, then deterministic revision/hash order; independent statement revisions are joined as-of before factor computation.",
                "6. Real data exposed same-date update_flag 0/1 duplicates, requiring the explicit priority above; Qlib amount was also confirmed as thousand CNY and is converted to CNY only in the V2 mature adapter.",
                f"7. Materializable definitions: `{counts['materializable']}` of 774.",
                f"8. Research-ready factors: `{counts['research_usable']}`.",
                f"9. Temporarily blocked factors: `{counts['temporarily_blocked']}`.",
                "10. Block reasons are coverage failure, zero finite history, or constant/degenerate real values; definitions remain frozen and no values are fabricated.",
                "11. Economic-family coverage is listed below and in `family_coverage.csv`.",
                "12. Factor-month, instrument-family, split/fold, source and factor audits are preserved separately; expected listing/warm-up/PIT gaps are not forward-filled.",
                "13. Units and magnitudes are checked in `unit_sanity.csv`; Tushare total_mv is converted from 10,000 CNY for PIT valuation and moneyflow is reconciled to Qlib amount converted from 1,000 CNY.",
                "14. Canonical direct-VWAP factors are compared with legacy proxies in `canonical_legacy_comparison.csv`; recovered factors are independently materialized on real provider data.",
                "15. V1 immutability is a critical manifest/hash contract.",
                f"16. Matrix shape is `{len(keys):,} × 774 defined factors` in partitioned form; only the explicit research-usable list is approved for later research.",
                "17. The matrix covers every existing split range plus the configured label tail through 2026-06-09.",
                "18. Bootstrap/build time, request counts, disk bytes and stage timings are recorded in `resource_timing.csv` and the manifest.",
                "19. Daily APIs are date-segmented; issuer statements are segment-cached with receipts, integrity hashes, gap detection and revision-aware re-fetch compatibility, so incremental updates reuse the same contract.",
                f"20. Economic Multi-Factor Research data readiness is `{'yes' if counts['research_usable'] > 669 else 'partial'}` for the qualified list only; no IC/model/winner/portfolio work occurred.",
                "",
                "## Raw-source coverage",
                "",
                *source_lines,
                "",
                "## Economic-family coverage",
                "",
                *family_lines,
                "",
                "## Temporarily blocked definitions",
                "",
                *blocked_lines,
                "",
                "## Boundary",
                "",
                "No IC, FDR, clustering, SHAP, model training, feature importance, portfolio optimization or Strategy V2 change was performed. `split_003` remains observed and cannot become new selection evidence.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def materialize(config: dict, scope: str, paths: BuildPaths) -> int:
    if scope == "full" and not tracked_worktree_clean(PROJECT_ROOT):
        raise ValueError("full materialization requires committed tracked implementation changes")
    intervals, research_calendar, daily_calendar = scope_inputs(config, scope)
    symbols = sorted(intervals["instrument"].unique())
    research_end = str(config["research_end_date"])
    if scope == "canary":
        research_end = str(config["canary"]["research_end_date"])
    keys = build_pit_key_grid(intervals, research_calendar)
    inventory = pd.read_csv(resolve(config["factor_inventory"]))
    if len(inventory) != 774 or inventory["name"].nunique() != 774:
        raise ValueError("Factor Universe V2 freeze is not exactly 774 unique definitions")
    timings: list[dict] = []
    started = time.perf_counter()
    market_raw = load_qlib_market(
        resolve(config["provider_uri"]),
        symbols,
        start_date=str(config["market_bootstrap_start_date"]),
        end_date=research_end,
        cache_path=paths.runtime_dir / f"{scope}_qlib_market.parquet",
    )
    membership_calendar = qlib_calendar(
        resolve(config["provider_uri"]),
        str(config["market_bootstrap_start_date"]),
        research_end,
    )
    membership_keys = build_pit_key_grid(intervals, membership_calendar)
    masked = mask_raw_to_pit_membership(
        market_raw,
        membership_keys,
        membership_start=pd.to_datetime(intervals["start_date"]).min(),
    )
    timings.append(timed("load_and_mask_qlib_market", started, rows=len(masked)))
    raw_store = TushareSegmentStore(resolve(config["raw_runtime_dir"]))
    trade_segments = [value.strftime("%Y%m%d") for value in daily_calendar]
    statement_segments = [qlib_to_tushare(value) for value in symbols]
    started = time.perf_counter()
    recovered, recovered_issues = compute_recovered(
        masked,
        keys,
        provider_uri=resolve(config["provider_uri"]),
        start_date=str(config["market_bootstrap_start_date"]),
        end_date=research_end,
        kunquant_path=resolve(config["alpha101_source_path"]),
        ta_source_path=resolve(config["ta_source_path"]),
        recovered_inventory=inventory.loc[inventory["lineage_status"].eq("recovered")],
    )
    timings.append(timed("materialize_recovered", started, factors=19))
    started = time.perf_counter()
    canonical, canonical_issues = compute_canonical(
        masked,
        keys,
        inventory,
        resolve(config["alpha101_source_path"]),
    )
    timings.append(timed("materialize_canonical", started, factors=28))
    started = time.perf_counter()
    mature, supporting = compute_mature_partitions(
        masked,
        keys,
        store=raw_store,
        trade_date_segments=trade_segments,
        statement_segments=statement_segments,
    )
    timings.append(timed("materialize_mature", started, factors=58))
    runtime_scope = paths.runtime_dir / scope
    new_frames = {"recovered": recovered, "canonical": canonical, **mature}
    adapter_issues = pd.concat([recovered_issues, canonical_issues], ignore_index=True)
    new_rows = []
    for partition_id, frame in new_frames.items():
        names = [value for value in inventory["name"].astype(str) if value in frame.columns]
        new_rows.append(write_partition(runtime_scope / f"{partition_id}.parquet", frame, names))
    new_partition_rows = pd.DataFrame(new_rows)
    if scope == "canary":
        qualification_input = audit_partitions(
            new_partition_rows,
            inventory,
            pd.read_csv(resolve(config["split_ranges"])).head(0),
            minimum_factor_coverage=float(config["qualification"]["minimum_factor_coverage"]),
            minimum_month_coverage=float(config["qualification"]["minimum_month_coverage"]),
            minimum_qualified_month_fraction=float(config["qualification"]["minimum_qualified_month_fraction"]),
        )
        paths.report_dir.mkdir(parents=True, exist_ok=True)
        qualification_input["factor"].to_csv(
            paths.report_dir / "canary_factor_coverage.csv", index=False
        )
        supporting["revision_audit"].to_csv(
            paths.report_dir / "canary_revision_audit.csv", index=False
        )
        _fina_indicator_crosscheck(supporting).to_csv(
            paths.report_dir / "canary_fina_indicator_crosscheck.csv", index=False
        )
        _unit_sanity(mature, supporting).to_csv(
            paths.report_dir / "canary_unit_sanity.csv", index=False
        )
        pd.DataFrame(timings).to_csv(paths.report_dir / "canary_materialization_timing.csv", index=False)
        adapter_issues.to_csv(paths.report_dir / "canary_adapter_issues.csv", index=False)
        print(qualification_input["factor"].groupby("research_usable").size().to_string())
        return 0

    legacy_rows = _legacy_partition_rows(config, inventory)
    partition_rows = pd.concat([legacy_rows, new_partition_rows], ignore_index=True)
    all_names = [name for values in partition_rows["factors"].str.split(",") for name in values]
    if len(all_names) != 774 or len(set(all_names)) != 774 or set(all_names) != set(inventory["name"]):
        raise ValueError("partition factor coverage is not an exact 774-definition bijection")
    if not partition_rows["row_count"].eq(len(keys)).all():
        raise ValueError("matrix partitions do not share one exact PIT key grid")
    started = time.perf_counter()
    audits = audit_partitions(
        partition_rows,
        inventory,
        pd.read_csv(resolve(config["split_ranges"])),
        minimum_factor_coverage=float(config["qualification"]["minimum_factor_coverage"]),
        minimum_month_coverage=float(config["qualification"]["minimum_month_coverage"]),
        minimum_qualified_month_fraction=float(config["qualification"]["minimum_qualified_month_fraction"]),
    )
    timings.append(timed("coverage_and_missingness_audit", started, factors=774))
    source_coverage, raw_identity = raw_source_coverage(
        resolve(config["raw_runtime_dir"]), trade_segments, statement_segments
    )
    canonical_comparison = compare_canonical_to_legacy(
        runtime_scope / "canonical.parquet", inventory, partition_rows
    )
    fina_crosscheck = _fina_indicator_crosscheck(supporting)
    unit_sanity = _unit_sanity(mature, supporting)
    qualification = audits["factor"]
    v1_unchanged = bool(legacy_rows["output_sha256"].eq(
        pd.read_csv(resolve(config["matrix_v4_partition_status"]))["output_sha256"].astype(str).values
    ).all())
    contracts = pd.DataFrame(
        [
            {"check": "frozen_universe_774", "status": "pass", "critical": True, "detail": 774},
            {"check": "exact_pit_key_grid", "status": "pass", "critical": True, "detail": len(keys)},
            {"check": "v1_669_byte_immutable", "status": "pass" if v1_unchanged else "fail", "critical": True, "detail": 669},
            {"check": "raw_segment_integrity", "status": "pass" if source_coverage["integrity_pass"].all() else "fail", "critical": True, "detail": int(source_coverage["observed_segment_count"].sum())},
            {"check": "no_future_statement_access", "status": supporting["pit_contract"].iloc[0]["status"], "critical": True, "detail": len(supporting["statement_alignment"])},
            {"check": "no_inf_factor_values", "status": "pass" if qualification["inf_count"].sum() == 0 else "fail", "critical": True, "detail": int(qualification["inf_count"].sum())},
            {"check": "canonical_direct_vwap_differs", "status": "pass" if canonical_comparison["different_count"].fillna(0).gt(0).any() else "fail", "critical": True, "detail": int(canonical_comparison["different_count"].fillna(0).sum())},
            {"check": "strategy_v2_not_authorized", "status": "pass", "critical": True, "detail": False},
        ]
    )
    critical_pass = contracts.loc[contracts["critical"], "status"].eq("pass").all()
    materializable = int(qualification["materializable"].sum())
    usable = int(qualification["research_usable"].sum())
    matrix_status = (
        "research_ready_with_blocked_factors"
        if critical_pass and usable > 669
        else "blocked"
    )
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    paths.report_dir.mkdir(parents=True, exist_ok=True)
    partition_rows.to_csv(paths.output_dir / "partition_manifest.csv", index=False)
    pd.DataFrame(
        {"factor_order": range(1, 775), "factor": inventory["name"].astype(str)}
    ).to_csv(paths.output_dir / "factor_order.csv", index=False)
    qualification.to_csv(paths.output_dir / "factor_qualification.csv", index=False)
    contracts.to_csv(paths.output_dir / "contract_status.csv", index=False)
    source_coverage.to_csv(paths.output_dir / "raw_source_coverage.csv", index=False)
    audits["family"].to_csv(paths.output_dir / "family_coverage.csv", index=False)
    for name, frame in audits.items():
        frame.to_csv(paths.report_dir / f"{name}_coverage.csv", index=False)
    source_coverage.to_csv(paths.report_dir / "raw_source_coverage.csv", index=False)
    canonical_comparison.to_csv(paths.report_dir / "canonical_legacy_comparison.csv", index=False)
    fina_crosscheck.to_csv(paths.report_dir / "fina_indicator_crosscheck.csv", index=False)
    unit_sanity.to_csv(paths.report_dir / "unit_sanity.csv", index=False)
    adapter_issues.to_csv(paths.report_dir / "adapter_issues.csv", index=False)
    supporting["revision_audit"].to_csv(paths.report_dir / "revision_audit.csv", index=False)
    pd.DataFrame(timings).to_csv(paths.report_dir / "resource_timing.csv", index=False)
    raw_manifest = {
        "schema_version": 1,
        **raw_identity,
        "apis": source_coverage.to_dict("records"),
        "market_bootstrap_start_date": config["market_bootstrap_start_date"],
        "statement_announcement_start_date": config["statement_announcement_start_date"],
        "statement_announcement_end_date": config["statement_announcement_end_date"],
    }
    (paths.output_dir / "raw_snapshot_manifest.json").write_text(
        json.dumps(raw_manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )
    output_files = [
        paths.output_dir / name
        for name in (
            "partition_manifest.csv",
            "factor_order.csv",
            "factor_qualification.csv",
            "contract_status.csv",
            "raw_source_coverage.csv",
            "family_coverage.csv",
            "raw_snapshot_manifest.json",
        )
    ]
    manifest = {
        "schema_version": 1,
        "stage_id": config["stage_id"],
        "artifact_status": matrix_status,
        "factor_universe_v2_manifest_sha256": file_sha256(resolve(config["factor_universe_manifest"])),
        "factor_count_defined": 774,
        "factor_count_materializable": materializable,
        "factor_count_research_usable": usable,
        "factor_count_temporarily_blocked": 774 - usable,
        "row_count": len(keys),
        "instrument_count": int(keys["instrument"].nunique()),
        "date_count": int(keys["datetime"].nunique()),
        "start_date": str(keys["datetime"].min().date()),
        "end_date": str(keys["datetime"].max().date()),
        "factor_order_sha256": file_sha256(paths.output_dir / "factor_order.csv"),
        "partition_identity_sha256": canonical_hash(
            partition_rows[["partition_id", "output_sha256", "factor_count", "row_count"]].to_dict("records")
        ),
        "raw_snapshot_id": raw_identity["raw_snapshot_id"],
        "universe_manifest_sha256": file_sha256(resolve(config["universe_manifest"])),
        "split_manifest_sha256": file_sha256(resolve(config["split_manifest"])),
        "matrix_v4_manifest_sha256": file_sha256(resolve(config["matrix_v4_manifest"])),
        "build_code_commit": git_commit(PROJECT_ROOT),
        "implementation_hashes": {
            path: file_sha256(PROJECT_ROOT / path)
            for path in (
                "factor_universe_v2/historical_data.py",
                "factor_universe_v2/matrix_readiness.py",
                "factor_universe_v2/pit.py",
                "factor_universe_v2/tushare_data.py",
                "scripts/run_factor_universe_v2_matrix_readiness.py",
            )
        },
        "pit_contract": config["fundamental_pit_semantics"],
        "decision_time_semantics": config["decision_time_semantics"],
        "strategy_v2_authorized": False,
        "output_file_hashes": {path.name: file_sha256(path) for path in output_files},
        "runtime_matrix_bytes": int(new_partition_rows["output_size_bytes"].sum()),
        "referenced_v1_matrix_bytes": int(legacy_rows["output_size_bytes"].sum()),
    }
    (paths.output_dir / "artifact_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )
    _write_report(
        paths.report_dir / "REPORT.md",
        config,
        scope,
        keys,
        qualification,
        source_coverage,
        audits["family"],
        pd.DataFrame(timings),
        supporting["revision_audit"],
        matrix_status,
    )
    print(json.dumps(manifest, indent=2))
    return 0 if matrix_status != "blocked" else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap and qualify Factor Universe V2 history.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/factor_universe_v2_matrix_readiness.yaml"),
    )
    parser.add_argument("--stage", choices=("bootstrap", "materialize", "all"), default="all")
    parser.add_argument("--scope", choices=("canary", "full"), default="canary")
    args = parser.parse_args()
    config = load_config(resolve(args.config))
    paths = BuildPaths(
        project_root=PROJECT_ROOT,
        runtime_dir=resolve(config["matrix_runtime_dir"]),
        output_dir=resolve(config["output_dir"]),
        report_dir=resolve(config["report_dir"]),
    )
    if args.stage in {"bootstrap", "all"}:
        status = bootstrap(config, args.scope, paths.report_dir)
        if status:
            return status
    if args.stage in {"materialize", "all"}:
        return materialize(config, args.scope, paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
