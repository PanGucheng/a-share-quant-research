from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_universe_v2.historical_data import STATEMENT_FIELDS  # noqa: E402
from research_validation.dataset_design import canonical_hash  # noqa: E402
from research_validation.historical_extension import parse_qlib_intervals  # noqa: E402
from research_validation.historical_data_authority import (  # noqa: E402
    assess_statement_completeness,
    authority_frontier,
    resolve_lifecycle_evidence,
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("invalid authority resolution configuration")
    return payload


def _query(pro: Any, receipts: list[dict[str, Any]], api: str, parameters: dict[str, Any]) -> pd.DataFrame:
    started = time.perf_counter()
    try:
        frame = pro.query(api, **parameters)
        status = "accessible_nonempty" if not frame.empty else "accessible_empty"
        receipts.append({
            "api": api, "parameters": json.dumps(parameters, sort_keys=True),
            "status": status, "row_count": len(frame),
            "columns": ",".join(map(str, frame.columns)),
            "content_sha256": canonical_hash(frame.to_dict("records")),
            "elapsed_seconds": round(time.perf_counter() - started, 3), "error": "",
        })
        return frame
    except Exception as exc:
        receipts.append({
            "api": api, "parameters": json.dumps(parameters, sort_keys=True),
            "status": "request_failed", "row_count": 0, "columns": "", "content_sha256": "",
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "error": f"{type(exc).__name__}: {exc}",
        })
        return pd.DataFrame()
    finally:
        time.sleep(0.15)


def probe(config: dict[str, Any], output_dir: Path) -> None:
    import tushare as ts

    token = os.environ.get("TUSHARE_TOKEN")
    if not token:
        raise RuntimeError("TUSHARE_TOKEN is required for authority resolution")
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    pro = ts.pro_api(token)
    receipts: list[dict[str, Any]] = []
    stock_basic = _query(pro, receipts, "stock_basic", {"exchange": "", "list_status": "", "fields": "ts_code,symbol,name,market,list_date,delist_date,list_status"})
    stock_basic.to_parquet(raw_dir / "stock_basic.parquet", index=False)
    codes = [str(code) for code in config["authority_codes"]]

    names: list[pd.DataFrame] = []
    for code in codes:
        names.append(_query(pro, receipts, "namechange", {"ts_code": code, "fields": "ts_code,name,start_date,end_date,change_reason"}))
    pd.concat(names, ignore_index=True).to_parquet(raw_dir / "namechange.parquet", index=False)

    presence: list[pd.DataFrame] = []
    market_fields = "ts_code,trade_date,close,vol,amount"
    for code in codes:
        for start_date, end_date in config["market_segments"]:
            frame = _query(pro, receipts, "daily", {"ts_code": code, "start_date": str(start_date), "end_date": str(end_date), "fields": market_fields})
            if not frame.empty:
                presence.append(pd.DataFrame({"instrument": frame["ts_code"], "date": pd.to_datetime(frame["trade_date"], format="%Y%m%d"), "source": "tushare_daily"}))

    # BaoStock is an independent historical presence/adjustment cross-check.  Store
    # only the bounded first/last evidence so the run remains small and auditable.
    baostock_rows: list[dict[str, Any]] = []
    try:
        import baostock as bs
        login = bs.login()
        if login.error_code == "0":
            try:
                for code in codes:
                    symbol = f"{code[-2:].lower()}.{code[:6]}"
                    result = bs.query_history_k_data_plus(symbol, "date,close,volume,amount,tradestatus,isST", start_date="2000-01-01", end_date="2021-12-31", frequency="d", adjustflag="3")
                    rows: list[list[str]] = []
                    while result.error_code == "0" and result.next():
                        rows.append(result.get_row_data())
                    frame = pd.DataFrame(rows, columns=result.fields or [])
                    baostock_rows.append({"instrument": code, "status": "success" if result.error_code == "0" else "request_failed", "row_count": len(frame), "first_date": frame["date"].min() if not frame.empty else "", "last_date": frame["date"].max() if not frame.empty else "", "tradestatus_nonzero_ratio": pd.to_numeric(frame.get("tradestatus", pd.Series(dtype=object)), errors="coerce").mean() if not frame.empty else None, "isST_rows": int(frame.get("isST", pd.Series(dtype=object)).astype(str).eq("1").sum()) if not frame.empty else 0, "error": result.error_msg if result.error_code != "0" else ""})
            finally:
                bs.logout()
        else:
            baostock_rows.append({"instrument": "__login__", "status": "request_failed", "row_count": 0, "first_date": "", "last_date": "", "tradestatus_nonzero_ratio": None, "isST_rows": 0, "error": f"{login.error_code}:{login.error_msg}"})
    except Exception as exc:
        baostock_rows.append({"instrument": "__module__", "status": "request_failed", "row_count": 0, "first_date": "", "last_date": "", "tradestatus_nonzero_ratio": None, "isST_rows": 0, "error": f"{type(exc).__name__}:{exc}"})
    pd.DataFrame(baostock_rows).to_csv(output_dir / "baostock_lifecycle_receipts.csv", index=False, encoding="utf-8-sig")

    # Statement retrieval is deliberately both broad+paginated and year-segmented.
    # The row-level key ledger allows the analyzer to prove whether segmentation
    # recovers all rows visible through the paginated endpoint.
    retrievals: list[dict[str, Any]] = []
    statement_rows: list[pd.DataFrame] = []
    for code in codes:
        for api, fields in STATEMENT_FIELDS.items():
            offset = 0
            page = 0
            while True:
                frame = _query(pro, receipts, api, {"ts_code": code, "start_date": config["statement_start_date"], "end_date": config["statement_end_date"], "fields": fields, "limit": int(config["statement_page_size"]), "offset": offset})
                terminal = len(frame) < int(config["statement_page_size"])
                retrievals.append({"api": api, "ts_code": code, "retrieval_mode": "paginated_broad", "segment_id": f"broad_{page}", "rows": len(frame), "row_cap_reached": len(frame) >= int(config["statement_page_size"]), "page_terminal": terminal})
                if not frame.empty:
                    ledger = frame.copy()
                    ledger["api"] = api
                    ledger["ts_code"] = code
                    ledger["retrieval_mode"] = "paginated_broad"
                    ledger["segment_id"] = f"broad_{page}"
                    statement_rows.append(ledger)
                if terminal:
                    break
                offset += int(config["statement_page_size"])
                page += 1
            periods = [f"{year}{month:02d}{day:02d}" for year in config["statement_years"] for month, day in ((3, 31), (6, 30), (9, 30), (12, 31))]
            for period in periods:
                offset = 0
                page = 0
                while True:
                    # ``period`` is the endpoint's exact report-period selector.
                    # Annual start/end windows are not equivalent: for example,
                    # income 2017-12-31 is announced in 2018 and is omitted by a
                    # 2017 calendar window.  Exact periods therefore close that
                    # retrieval gap while preserving all revisions for the period.
                    frame = _query(pro, receipts, api, {"ts_code": code, "period": period, "fields": fields, "limit": int(config["statement_page_size"]), "offset": offset})
                    terminal = len(frame) < int(config["statement_page_size"])
                    retrievals.append({"api": api, "ts_code": code, "retrieval_mode": "segmented_period", "segment_id": f"{period}_{page}", "rows": len(frame), "row_cap_reached": len(frame) >= int(config["statement_page_size"]), "page_terminal": terminal})
                    if not frame.empty:
                        ledger = frame.copy()
                        ledger["api"] = api
                        ledger["ts_code"] = code
                        ledger["retrieval_mode"] = "segmented_period"
                        ledger["segment_id"] = f"{period}_{page}"
                        statement_rows.append(ledger)
                    if terminal:
                        break
                    offset += int(config["statement_page_size"])
                    page += 1
    pd.DataFrame(retrievals).to_csv(output_dir / "statement_retrieval_receipts.csv", index=False, encoding="utf-8-sig")
    if statement_rows:
        pd.concat(statement_rows, ignore_index=True).to_parquet(raw_dir / "statement_rows.parquet", index=False)
    pd.concat(presence, ignore_index=True).drop_duplicates().to_parquet(raw_dir / "market_presence.parquet", index=False) if presence else pd.DataFrame(columns=["instrument", "date", "source"]).to_parquet(raw_dir / "market_presence.parquet", index=False)
    pd.DataFrame(receipts).to_csv(output_dir / "network_receipts.csv", index=False, encoding="utf-8-sig")
    (output_dir / "probe_complete.json").write_text(json.dumps({"authority_code_count": len(codes), "statement_request_count": len(retrievals), "tushare_token_used": True, "token_persisted": False}, indent=2) + "\n", encoding="utf-8")


def analyze(config: dict[str, Any], output_dir: Path) -> None:
    raw_dir = output_dir / "raw"
    stock_basic = pd.read_parquet(raw_dir / "stock_basic.parquet")
    intervals = parse_qlib_intervals(resolve(config["qlib_interval_file"]))
    presence = pd.read_parquet(raw_dir / "market_presence.parquet")
    names = pd.read_parquet(raw_dir / "namechange.parquet")
    lifecycle, lifecycle_summary = resolve_lifecycle_evidence(stock_basic, intervals, presence, names)
    lifecycle.to_csv(output_dir / "lifecycle_reconciliation.csv", index=False, encoding="utf-8-sig")
    lifecycle_summary.to_csv(output_dir / "lifecycle_authority_summary.csv", index=False, encoding="utf-8-sig")

    receipts = pd.read_csv(output_dir / "statement_retrieval_receipts.csv")
    statement_detail, statement_summary = assess_statement_completeness(receipts)
    rows = pd.read_parquet(raw_dir / "statement_rows.parquet") if (raw_dir / "statement_rows.parquet").is_file() else pd.DataFrame()
    compare: list[dict[str, Any]] = []
    if not rows.empty:
        key_cols = [c for c in ("ts_code", "end_date", "report_type", "ann_date", "update_flag") if c in rows.columns]
        for (api, code), group in rows.groupby(["api", "ts_code"]):
            end_year = pd.to_datetime(group["end_date"], format="%Y%m%d", errors="coerce").dt.year
            target = end_year.isin(config["statement_years"])
            broad = group.loc[group["retrieval_mode"].eq("paginated_broad") & target, key_cols].astype(str).drop_duplicates()
            segmented = group.loc[group["retrieval_mode"].eq("segmented_period") & target, key_cols].astype(str).drop_duplicates()
            broad_keys = set(map(tuple, broad.to_numpy()))
            segmented_keys = set(map(tuple, segmented.to_numpy()))
            compare.append({"api": api, "ts_code": code, "broad_target_key_count": len(broad_keys), "segmented_key_count": len(segmented_keys), "broad_missing_from_segmented": len(broad_keys - segmented_keys), "segmented_not_in_broad": len(segmented_keys - broad_keys), "target_key_sets_equal": broad_keys == segmented_keys})
    comparison = pd.DataFrame(compare)
    comparison.to_csv(output_dir / "statement_key_set_comparison.csv", index=False, encoding="utf-8-sig")
    if not comparison.empty:
        statement_summary = statement_summary.merge(comparison.groupby("api", as_index=False).agg(target_key_set_equal=("target_key_sets_equal", "all")), on="api", how="left")
        statement_summary["provider_vintage_complete"] = False
        statement_summary["authority_status"] = statement_summary.apply(lambda row: "retrieval_complete_provider_vintage_unproven" if row["retrieval_complete_rate"] == 1.0 and bool(row.get("target_key_set_equal", False)) else "blocked_retrieval_incomplete", axis=1)
    statement_detail.to_csv(output_dir / "statement_completeness_detail.csv", index=False, encoding="utf-8-sig")
    statement_summary.to_csv(output_dir / "statement_completeness_summary.csv", index=False, encoding="utf-8-sig")

    prior = Path(config["prior_frontier_dir"])
    coverage = pd.read_csv(resolve(prior / "market_coverage.csv"))
    frontiers = pd.DataFrame([authority_frontier(coverage, lifecycle_summary, statement_summary, layer=layer, minimum_coverage=float(config["minimum_market_coverage"])) for layer in ("daily_basic", "moneyflow")])
    frontiers.to_csv(output_dir / "recomputed_frontiers.csv", index=False, encoding="utf-8-sig")

    decisions = pd.DataFrame([
        ["lifecycle_authority", "blocked", "Qlib interval + current Tushare metadata + dated market cross-check form a reproducible candidate, but no historical provider vintage is proven."],
        ["survivorship_control", "blocked", "Current stock_basic is a snapshot; delisted/namechange evidence is not a dated membership vintage."],
        ["statement_retrieval_completeness", "pass" if not statement_summary.empty and statement_summary["retrieval_complete_rate"].eq(1.0).all() else "blocked", "Segmented annual requests and offset pagination are audited; this proves endpoint retrieval completeness only."],
        ["fundamental_pit_provider_vintage", "blocked", "Announcement/revision history is not independently versioned by the provider; retrieval completeness is not vintage completeness."],
        ["daily_basic_moneyflow_frontier", "not_admitted", "Candidate dates are recomputed, but authority gates remain blocked."],
        ["full_factor_universe_v2_common_frontier", "not_admitted", "Lifecycle and fundamental PIT authority remain blocked."],
        ["extended_matrix", "not_generated", "No new Matrix is created while authority gates are blocked."],
    ], columns=["decision_area", "status", "reason"])
    decisions.to_csv(output_dir / "qualification_decision.csv", index=False, encoding="utf-8-sig")
    report = """# Historical Data Authority Resolution V1

> 状态：`QUALIFICATION COMPLETE / AUTHORITY UNRESOLVED / EXTENDED MATRIX NOT GENERATED`。

## 结论

- Lifecycle 的最佳可复现候选是 **Community Qlib interval + Tushare stock_basic/namechange + Tushare/BaoStock dated market presence cross-check**。这能构造 listing/delisting/rename 的候选区间，但 Qlib 是 release snapshot、Tushare stock_basic 是 current snapshot，故不能证明任意历史日期的 historical vintage；survivorship-control gate 仍 blocked。
- Fundamental retrieval 已改为 broad offset pagination 与 2010–2017 exact report-period segmentation（使用 `period=YYYYMMDD`，避免公告跨年导致的 calendar-window 漏行）。`statement_completeness_summary.csv` 记录每个 issuer/API 是否所有页终止、是否触及 cap、以及目标期 key set 是否一致。即使通过，这只证明当前 endpoint 的 retrieval completeness，不证明 provider 保存的 revision vintage 完整；PIT authority 仍 blocked。
- `recomputed_frontiers.csv` 重新计算 daily_basic/moneyflow 的 coverage candidate，但 `authoritative=false`，不能把此前 `2016-07` 等候选升级为正式 frontier。
- Full Factor Universe V2 common frontier：`not_admitted`；Extended Matrix：`not_generated`。

## 证据与限制

本轮没有读取 model outcomes，没有修改 Research Protocol V2、Factor Universe V2 definitions、Strategy V1、Forward Track 或旧 frozen Matrix。网络请求 receipts、statement retrieval receipts、raw parquet 与 manifest 均保留；token 未写入 artifacts。

治理状态：

```text
extended_matrix_generated = false
formal_structured_ml_competition_started = false
research_protocol_v2_changed = false
factor_universe_v2_definitions_changed = false
frozen_matrix_changed = false
strategy_v1_changed = false
forward_track_changed = false
model_outcomes_read = false
```

复现：

```powershell
E:\\anaconda_envs\\qlib_env\\python.exe scripts\\run_historical_data_authority_resolution_v1.py --stage all
```
"""
    (output_dir / "REPORT.md").write_text(report, encoding="utf-8")


def finalize(config_path: Path, config: dict[str, Any], output_dir: Path) -> None:
    files = sorted(path for path in output_dir.rglob("*") if path.is_file() and path.name != "manifest.json")
    manifest = {
        "schema_version": 1, "stage_id": config["stage_id"],
        "artifact_status": "qualification_complete_authority_unresolved",
        "config_sha256": sha256(config_path), "extended_matrix_generated": False,
        "formal_structured_ml_competition_started": False, "research_protocol_v2_changed": False,
        "factor_universe_v2_definitions_changed": False, "frozen_matrix_changed": False,
        "strategy_v1_changed": False, "forward_track_changed": False, "model_outcomes_read": False,
        "network_receipts_present": (output_dir / "network_receipts.csv").is_file(),
        "output_file_hashes": {str(path.relative_to(output_dir)): sha256(path) for path in files},
    }
    manifest["manifest_identity"] = canonical_hash(manifest["output_file_hashes"])
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Historical Data Authority Resolution V1")
    parser.add_argument("--config", type=Path, default=Path("configs/historical_data_authority_resolution_v1.yaml"))
    parser.add_argument("--stage", choices=("probe", "analyze", "finalize", "all"), default="all")
    args = parser.parse_args()
    config_path = resolve(args.config)
    config = load_config(config_path)
    output_dir = resolve(config["output_dir"])
    if args.stage in {"probe", "all"}:
        probe(config, output_dir)
    if args.stage in {"analyze", "all"}:
        analyze(config, output_dir)
    if args.stage in {"finalize", "all"}:
        finalize(config_path, config, output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
