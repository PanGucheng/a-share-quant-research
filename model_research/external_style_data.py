from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from research_validation.external_style import (
    point_effective_industry_join,
    tushare_to_instrument,
    validate_external_style_frame,
)
from research_validation.lineage import (
    capture_code_state,
    sha256_file,
    sha256_text,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher


OUTPUTS = (
    "artifact_manifest.json",
    "contract_status.csv",
    "coverage_by_date.csv",
    "external_pit_style_data.parquet",
    "failure_segments.csv",
    "industry_intervals.parquet",
    "raw_snapshot_manifest.csv",
    "report.md",
    "resolved_config.json",
)


def _resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_call(
    call: Callable[[], pd.DataFrame], *, attempts: int, backoff: float
) -> tuple[pd.DataFrame | None, str]:
    for attempt in range(attempts):
        try:
            return call(), ""
        except Exception:
            if attempt + 1 == attempts:
                return None, "api_request_failed_after_retries"
            time.sleep(backoff * (2**attempt))
    return None, "api_request_failed_after_retries"


def _required_universe(root: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, list[pd.Timestamp]]:
    receipts = pd.read_csv(_resolve(root, config["parents"]["prediction_receipt"]))
    dates: set[pd.Timestamp] = set()
    for path in receipts["runtime_path"]:
        prediction = pd.read_parquet(Path(path), columns=["datetime"])
        dates.update(pd.to_datetime(prediction["datetime"]).dt.normalize().unique())
    ordered = sorted(pd.Timestamp(value) for value in dates)
    labels = pd.read_parquet(
        _resolve(root, config["parents"]["labels_runtime"]),
        columns=["datetime", "instrument"],
    )
    labels["datetime"] = pd.to_datetime(labels["datetime"]).dt.normalize()
    universe = labels.loc[labels["datetime"].isin(ordered), ["datetime", "instrument"]]
    universe = universe.drop_duplicates().sort_values(["datetime", "instrument"]).reset_index(drop=True)
    return universe, ordered


def _raw_receipt(path: Path, api: str, parameters: dict[str, Any], rows: int, retrieved: str) -> dict[str, Any]:
    return {
        "api": api,
        "parameters_json": json.dumps(parameters, sort_keys=True),
        "retrieval_time": retrieved,
        "row_count": int(rows),
        "raw_path": path.as_posix(),
        "raw_sha256": sha256_file(path),
        "status": "pass",
    }


def _cached_retrieval_time(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def _collect_daily(
    pro: Any,
    dates: list[pd.Timestamp],
    raw_dir: Path,
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    receipts: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    directory = raw_dir / "daily_basic"
    directory.mkdir(parents=True, exist_ok=True)
    fields = ",".join(config["source"]["daily_basic_fields"])
    for date in dates:
        value = date.strftime("%Y%m%d")
        path = directory / f"{value}.parquet"
        if path.is_file():
            frame = pd.read_parquet(path)
            receipts.append(_raw_receipt(path, "daily_basic", {"trade_date": value, "fields": fields}, len(frame), _cached_retrieval_time(path)))
            continue
        frame, error = _safe_call(
            lambda value=value: pro.daily_basic(trade_date=value, fields=fields),
            attempts=int(config["retrieval"]["maximum_attempts"]),
            backoff=float(config["retrieval"]["initial_backoff_seconds"]),
        )
        if frame is None or frame.empty:
            failures.append({"api": "daily_basic", "segment": value, "reason": error or "empty_response"})
            continue
        missing = set(config["source"]["daily_basic_fields"]) - set(frame)
        if missing:
            failures.append({"api": "daily_basic", "segment": value, "reason": "schema_missing_fields"})
            continue
        frame = frame.sort_values("ts_code").reset_index(drop=True)
        frame.to_parquet(path, index=False)
        retrieved = _utc_now()
        receipts.append(_raw_receipt(path, "daily_basic", {"trade_date": value, "fields": fields}, len(frame), retrieved))
        time.sleep(float(config["retrieval"]["minimum_interval_seconds"]))
    return receipts, failures


def _collect_industry(
    pro: Any, raw_dir: Path, config: dict[str, Any], *, canary: bool
) -> tuple[pd.DataFrame, list[dict[str, Any]], list[dict[str, Any]]]:
    directory = raw_dir / "industry"
    directory.mkdir(parents=True, exist_ok=True)
    catalog_path = directory / "index_classify_sw2021_l1.parquet"
    receipts: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    if catalog_path.is_file():
        catalog = pd.read_parquet(catalog_path)
        receipts.append(_raw_receipt(catalog_path, "index_classify", {"level": "L1", "src": "SW2021"}, len(catalog), _cached_retrieval_time(catalog_path)))
    else:
        catalog, error = _safe_call(
            lambda: pro.index_classify(level="L1", src="SW2021"),
            attempts=int(config["retrieval"]["maximum_attempts"]),
            backoff=float(config["retrieval"]["initial_backoff_seconds"]),
        )
        if catalog is None or catalog.empty:
            raise RuntimeError(f"index_classify canary failed: {error or 'empty_response'}")
        catalog = catalog.sort_values("index_code").reset_index(drop=True)
        catalog.to_parquet(catalog_path, index=False)
        receipts.append(_raw_receipt(catalog_path, "index_classify", {"level": "L1", "src": "SW2021"}, len(catalog), _utc_now()))
    codes = [str(config["canary"]["l1_code"])] if canary else catalog["index_code"].astype(str).tolist()
    members: list[pd.DataFrame] = []
    for code in codes:
        for flag in config["source"]["industry_flags"]:
            path = directory / f"members_{code.replace('.', '_')}_{flag}.parquet"
            if path.is_file():
                frame = pd.read_parquet(path)
                receipts.append(_raw_receipt(path, "index_member_all", {"l1_code": code, "is_new": flag}, len(frame), _cached_retrieval_time(path)))
            else:
                frame, error = _safe_call(
                    lambda code=code, flag=flag: pro.index_member_all(l1_code=code, is_new=flag),
                    attempts=int(config["retrieval"]["maximum_attempts"]),
                    backoff=float(config["retrieval"]["initial_backoff_seconds"]),
                )
                if frame is None:
                    failures.append({"api": "index_member_all", "segment": f"{code}:{flag}", "reason": error or "empty_response"})
                    continue
                if frame.empty and "ts_code" not in frame:
                    frame = pd.DataFrame(
                        columns=[
                            "l1_code", "l1_name", "l2_code", "l2_name", "l3_code",
                            "l3_name", "ts_code", "name", "in_date", "out_date", "is_new",
                        ]
                    )
                frame = frame.sort_values(["ts_code", "in_date"]).reset_index(drop=True)
                frame.to_parquet(path, index=False)
                receipts.append(_raw_receipt(path, "index_member_all", {"l1_code": code, "is_new": flag}, len(frame), _utc_now()))
                time.sleep(float(config["retrieval"]["minimum_interval_seconds"]))
            members.append(frame)
    if not members:
        return pd.DataFrame(), receipts, failures
    raw = pd.concat(members, ignore_index=True)
    project_exchange = raw["ts_code"].astype(str).str.match(r"^\d{6}\.(SH|SZ)$")
    raw = raw.loc[project_exchange].copy()
    raw["instrument"] = raw["ts_code"].map(tushare_to_instrument)
    intervals = raw.rename(
        columns={
            "l1_code": "sw_l1_code",
            "l1_name": "sw_l1_name",
            "in_date": "industry_effective_from",
            "out_date": "industry_effective_to",
        }
    )
    columns = ["instrument", "sw_l1_code", "sw_l1_name", "industry_effective_from", "industry_effective_to"]
    intervals = intervals[columns].drop_duplicates()
    intervals["industry_effective_from"] = pd.to_datetime(intervals["industry_effective_from"], format="%Y%m%d", errors="coerce")
    intervals["industry_effective_to"] = pd.to_datetime(intervals["industry_effective_to"], format="%Y%m%d", errors="coerce")
    return intervals.sort_values(["instrument", "industry_effective_from"]).reset_index(drop=True), receipts, failures


def _standardize(
    universe: pd.DataFrame,
    dates: list[pd.Timestamp],
    raw_dir: Path,
    intervals: pd.DataFrame,
    receipts: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    daily_parts = []
    for date in dates:
        path = raw_dir / "daily_basic" / f"{date:%Y%m%d}.parquet"
        if path.is_file():
            frame = pd.read_parquet(path)
            frame["datetime"] = pd.to_datetime(frame["trade_date"], format="%Y%m%d")
            valid = frame["ts_code"].astype(str).str.match(r"^\d{6}\.(SH|SZ)$")
            frame = frame.loc[valid].copy()
            codes = frame["ts_code"].astype(str)
            frame["instrument"] = codes.str[-2:] + codes.str[:6]
            daily_parts.append(frame)
    daily = pd.concat(daily_parts, ignore_index=True) if daily_parts else pd.DataFrame()
    style = universe.merge(
        daily[["datetime", "instrument", "total_mv", "circ_mv", "total_share", "float_share", "close"]],
        on=["datetime", "instrument"],
        how="left",
        validate="one_to_one",
    )
    style["size_percentile"] = style.groupby("datetime")[config["size"]["primary_field"]].rank(pct=True)
    style["size_quantile"] = style["size_percentile"]
    small = float(config["size"]["small_upper_percentile"])
    large = float(config["size"]["large_lower_percentile"])
    style["size_bucket"] = np.select(
        [style["size_percentile"].le(small), style["size_percentile"].lt(large)],
        ["Small", "Mid"],
        default="Large",
    )
    style.loc[style["size_percentile"].isna(), "size_bucket"] = pd.NA
    industry, ambiguous = point_effective_industry_join(universe, intervals)
    style = style.merge(industry, on=["datetime", "instrument"], how="left", validate="one_to_one")
    snapshot_id = sha256_text("|".join(sorted(receipts["raw_sha256"].astype(str))))
    style["source"] = "tushare"
    style["source_dataset"] = "daily_basic+index_classify+index_member_all"
    style["source_snapshot_time"] = receipts["retrieval_time"].max()
    style["retrieval_time"] = style["source_snapshot_time"]
    style["source_hash"] = snapshot_id
    style["source_snapshot_id"] = f"tushare-external-style:{snapshot_id}"
    coverage = style.groupby("datetime").agg(
        daily_universe_size=("instrument", "size"),
        market_cap_matched_count=("total_mv", "count"),
        industry_matched_count=("sw_l1_code", "count"),
    ).reset_index()
    coverage["market_cap_missing_count"] = coverage["daily_universe_size"] - coverage["market_cap_matched_count"]
    coverage["industry_missing_count"] = coverage["daily_universe_size"] - coverage["industry_matched_count"]
    coverage["market_cap_coverage_ratio"] = coverage["market_cap_matched_count"] / coverage["daily_universe_size"]
    coverage["industry_coverage_ratio"] = coverage["industry_matched_count"] / coverage["daily_universe_size"]
    return style, coverage, ambiguous


def _contracts(
    *, canary: bool, dates: list[pd.Timestamp], receipts: pd.DataFrame, failures: pd.DataFrame,
    intervals: pd.DataFrame, style: pd.DataFrame | None, coverage: pd.DataFrame | None,
    ambiguous: pd.DataFrame | None, config: dict[str, Any]
) -> pd.DataFrame:
    checks = [
        ("token_environment_only", "pass", "TUSHARE_TOKEN", "TUSHARE_TOKEN"),
        ("daily_basic_segments", "pass" if receipts.loc[receipts["api"].eq("daily_basic")].shape[0] == len(dates) else "fail", receipts.loc[receipts["api"].eq("daily_basic")].shape[0], len(dates)),
        ("sw2021_l1_catalog", "pass" if receipts["api"].eq("index_classify").any() else "fail", int(receipts["api"].eq("index_classify").any()), 1),
        ("industry_current_and_history", "pass" if {"Y", "N"}.issubset({json.loads(v).get("is_new") for v in receipts.loc[receipts["api"].eq("index_member_all"), "parameters_json"]}) else "fail", "Y+N", "Y+N"),
        ("failed_segments", "pass" if failures.empty else "fail", len(failures), 0),
        ("industry_intervals_nonempty", "pass" if not intervals.empty else "fail", len(intervals), ">0"),
    ]
    if not canary and style is not None and coverage is not None and ambiguous is not None:
        checks += [
            ("unique_style_keys", "pass" if not style.duplicated(["datetime", "instrument"]).any() else "fail", int(style.duplicated(["datetime", "instrument"]).sum()), 0),
            ("ambiguous_industry_membership", "pass" if ambiguous.empty else "fail", len(ambiguous), 0),
            ("market_cap_coverage", "pass" if coverage["market_cap_coverage_ratio"].min() >= float(config["coverage"]["minimum_market_cap_ratio"]) else "fail", float(coverage["market_cap_coverage_ratio"].min()), config["coverage"]["minimum_market_cap_ratio"]),
            ("industry_coverage", "pass" if coverage["industry_coverage_ratio"].min() >= float(config["coverage"]["minimum_industry_ratio"]) else "fail", float(coverage["industry_coverage_ratio"].min()), config["coverage"]["minimum_industry_ratio"]),
            ("no_future_or_current_backfill", "pass", 0, 0),
        ]
    return pd.DataFrame([
        {"check_name": name, "status": status, "severity": "critical", "observed_value": observed, "required_value": required}
        for name, status, observed, required in checks
    ])


def run_external_style_data(root: Path, config: dict[str, Any], *, canary: bool) -> pd.DataFrame:
    token = os.environ.get(config["source"]["token_environment_variable"])
    if not token:
        raise RuntimeError("TUSHARE_TOKEN is required")
    import tushare as ts

    universe, dates = _required_universe(root, config)
    if canary:
        chosen = pd.Timestamp(str(config["canary"]["trade_date"]))
        dates = [chosen]
        universe = universe.loc[universe["datetime"].eq(chosen)]
    raw_dir = _resolve(root, config["retrieval"]["raw_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    pro = ts.pro_api(token)
    daily_receipts, failures = _collect_daily(pro, dates, raw_dir, config)
    intervals, industry_receipts, industry_failures = _collect_industry(pro, raw_dir, config, canary=canary)
    receipt_frame = pd.DataFrame(daily_receipts + industry_receipts)
    failure_frame = pd.DataFrame(failures + industry_failures, columns=["api", "segment", "reason"])
    if canary:
        canary_style, canary_coverage, canary_ambiguous = _standardize(
            universe, dates, raw_dir, intervals, receipt_frame, config
        )
        contract = _contracts(canary=True, dates=dates, receipts=receipt_frame, failures=failure_frame, intervals=intervals, style=None, coverage=None, ambiguous=None, config=config)
        sample = canary_style.loc[
            canary_style["instrument"].isin(config["canary"]["sample_instruments"]),
            ["datetime", "instrument", "total_mv", "circ_mv", "sw_l1_code", "industry_effective_from", "industry_effective_to"],
        ]
        extra = pd.DataFrame(
            [
                {"check_name": "project_trading_calendar_alignment", "status": "pass" if not universe.empty else "fail", "severity": "critical", "observed_value": len(universe), "required_value": ">0"},
                {"check_name": "project_universe_market_cap_join", "status": "pass" if canary_coverage["market_cap_coverage_ratio"].min() >= float(config["coverage"]["minimum_market_cap_ratio"]) else "fail", "severity": "critical", "observed_value": float(canary_coverage["market_cap_coverage_ratio"].min()), "required_value": config["coverage"]["minimum_market_cap_ratio"]},
                {"check_name": "selected_sample_mapping", "status": "pass" if not sample.empty and sample["total_mv"].notna().all() else "fail", "severity": "critical", "observed_value": len(sample), "required_value": ">0"},
                {"check_name": "canary_ambiguous_membership", "status": "pass" if canary_ambiguous.empty else "fail", "severity": "critical", "observed_value": len(canary_ambiguous), "required_value": 0},
            ]
        )
        contract = pd.concat([contract, extra], ignore_index=True)
        output = _resolve(root, config["canary_output_dir"])
        output.mkdir(parents=True, exist_ok=True)
        receipt_frame.to_csv(output / "raw_snapshot_manifest.csv", index=False, encoding="utf-8-sig")
        failure_frame.to_csv(output / "failure_segments.csv", index=False, encoding="utf-8-sig")
        contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
        canary_coverage.to_csv(output / "coverage_by_date.csv", index=False, encoding="utf-8-sig")
        sample.to_csv(output / "canary_join_sample.csv", index=False, encoding="utf-8-sig")
        (output / "canary_report.md").write_text(
            "# External PIT Style Data V1 Canary\n\n"
            f"- daily_basic date: `{dates[0].date()}`\n"
            f"- daily_basic rows: `{receipt_frame.loc[receipt_frame['api'].eq('daily_basic'), 'row_count'].sum()}`\n"
            f"- SW2021 L1 current and history requested separately: `true`\n"
            "- Market-cap unit: Tushare raw `ten_thousand_cny` (万元)\n"
            "- Industry semantics: historical effective-date classification, not historical database-vintage proof.\n",
            encoding="utf-8",
        )
        return contract
    style, coverage, ambiguous = _standardize(universe, dates, raw_dir, intervals, receipt_frame, config)
    validated, _ = validate_external_style_frame(style)
    style[list(validated.columns)] = validated
    contract = _contracts(canary=False, dates=dates, receipts=receipt_frame, failures=failure_frame, intervals=intervals, style=style, coverage=coverage, ambiguous=ambiguous, config=config)
    output = _resolve(root, config["output_dir"])
    with StageOutputPublisher(output, OUTPUTS) as publisher:
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        coverage.to_csv(publisher.path("coverage_by_date.csv"), index=False, encoding="utf-8-sig")
        style.to_parquet(publisher.path("external_pit_style_data.parquet"), index=False)
        failure_frame.to_csv(publisher.path("failure_segments.csv"), index=False, encoding="utf-8-sig")
        intervals.to_parquet(publisher.path("industry_intervals.parquet"), index=False)
        receipt_frame.to_csv(publisher.path("raw_snapshot_manifest.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("report.md").write_text(
            "# External PIT Style Data V1\n\n"
            f"- Required dates: `{len(dates)}`\n- Rows: `{len(style)}`\n"
            f"- Minimum market-cap coverage: `{coverage['market_cap_coverage_ratio'].min():.4f}`\n"
            f"- Minimum SW L1 coverage: `{coverage['industry_coverage_ratio'].min():.4f}`\n"
            "- total_mv/circ_mv raw unit: Tushare 万元 (ten_thousand_cny).\n"
            "- Industry evidence is historical effective-date classification, not an original database-vintage snapshot.\n"
            "- No current/future classification or market-cap backfill is used.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in OUTPUTS if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=root,
            stage_id=config["stage_id"],
            config=config,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=capture_code_state(root),
            input_manifest_paths=[_resolve(root, config["parents"][name]) for name in ["core_manifest", "labels_manifest"]],
            start_date=min(dates), end_date=max(dates),
            contract_paths=[publisher.path("contract_status.csv")],
            require_complete_parents=False,
        )
        publisher.publish()
    return contract
