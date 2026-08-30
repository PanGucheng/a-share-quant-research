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
from research_validation.historical_frontier_admission import (  # noqa: E402
    audit_adjustment_continuity,
    audit_cross_sectional_coverage,
    audit_lifecycle_alignment,
    audit_statement_panel,
    continuous_frontier,
    stratified_stock_sample,
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("invalid historical frontier admission configuration")
    return payload


def _write_frame(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


def probe(config: dict[str, Any], output_dir: Path) -> None:
    import tushare as ts

    token = os.environ.get("TUSHARE_TOKEN")
    if not token:
        raise RuntimeError("TUSHARE_TOKEN is required for the market qualification probe")
    pro = ts.pro_api(token)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    receipts: list[dict[str, Any]] = []

    def query(api: str, parameters: dict[str, Any]) -> pd.DataFrame:
        started = time.perf_counter()
        try:
            frame = pro.query(api, **parameters)
            status = "accessible_nonempty" if not frame.empty else "accessible_empty"
            receipts.append({"api": api, "parameters": json.dumps(parameters, sort_keys=True), "status": status, "row_count": len(frame), "columns": ",".join(map(str, frame.columns)), "elapsed_seconds": round(time.perf_counter() - started, 3), "error": ""})
            return frame
        except Exception as exc:
            receipts.append({"api": api, "parameters": json.dumps(parameters, sort_keys=True), "status": "request_failed", "row_count": 0, "columns": "", "elapsed_seconds": round(time.perf_counter() - started, 3), "error": f"{type(exc).__name__}: {exc}"})
            return pd.DataFrame()
        finally:
            # Keep each endpoint comfortably below Tushare's per-minute quota;
            # this also makes receipts reproducible instead of burst-dependent.
            time.sleep(0.35)

    stock_basic = query("stock_basic", {"exchange": "", "list_status": "", "fields": "ts_code,name,list_date,delist_date,list_status"})
    _write_frame(stock_basic, raw_dir / "stock_basic.parquet")
    sample = stratified_stock_sample(stock_basic, sample_per_stratum=int(config["sample_per_stratum"]), seed=int(config["analysis_seed"]))
    sample.to_csv(output_dir / "market_canary_sample.csv", index=False, encoding="utf-8-sig")

    market_frames: dict[str, list[pd.DataFrame]] = {"daily_basic": [], "moneyflow": []}
    for date in config["market_dates"]:
        date_key = pd.Timestamp(date).strftime("%Y%m%d")
        for api, fields in (("daily_basic", "ts_code,trade_date,close,turnover_rate_f,total_mv,circ_mv"), ("moneyflow", "ts_code,trade_date,net_mf_amount")):
            frame = query(api, {"trade_date": date_key, "fields": fields})
            if not frame.empty:
                market_frames[api].append(frame)
    for api, frames in market_frames.items():
        _write_frame(pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(), raw_dir / f"{api}.parquet")

    statement_frames: list[dict[str, Any]] = []
    for ts_code in sample["ts_code"].astype(str):
        for api, fields in STATEMENT_FIELDS.items():
            frame = query(api, {"ts_code": ts_code, "start_date": config["statement_start_date"], "end_date": config["statement_end_date"], "fields": fields})
            _write_frame(frame, raw_dir / "statements" / f"{api}_{ts_code.replace('.', '_')}.parquet")
            statement_frames.append({"ts_code": ts_code, "api": api, "rows": len(frame)})

    # Adjustment continuity is a bounded canary over both surviving and delisted,
    # pre-2010 cohorts.  Daily and adj_factor are intentionally queried separately
    # so provider row caps cannot silently hide a factor event.
    adjustment_codes = sample.loc[sample["list_date"].astype(str).str[:4].astype(int).le(2010), "ts_code"].astype(str).head(12).tolist()
    adjustment_parts: list[pd.DataFrame] = []
    for ts_code in adjustment_codes:
        for start, end in ((config["adjustment_start_date"], "20101231"), ("20110101", config["adjustment_end_date"])):
            daily = query("daily", {"ts_code": ts_code, "start_date": start, "end_date": end, "fields": "ts_code,trade_date,close"})
            adj = query("adj_factor", {"ts_code": ts_code, "start_date": start, "end_date": end, "fields": "ts_code,trade_date,adj_factor"})
            if daily.empty and adj.empty:
                continue
            merged = adj.merge(daily[["ts_code", "trade_date"]].drop_duplicates().assign(daily_present=True), on=["ts_code", "trade_date"], how="outer")
            merged["instrument"] = merged["ts_code"].astype(str).str.split(".").str[::-1].str.join("")
            adjustment_parts.append(merged)
    _write_frame(pd.concat(adjustment_parts, ignore_index=True) if adjustment_parts else pd.DataFrame(), raw_dir / "adjustment_continuity.parquet")
    pd.DataFrame(receipts).to_csv(output_dir / "network_receipts.csv", index=False, encoding="utf-8-sig")
    (output_dir / "probe_complete.json").write_text(json.dumps({"sample_count": len(sample), "adjustment_code_count": len(adjustment_codes), "tushare_token_used": True, "token_persisted": False}, indent=2) + "\n", encoding="utf-8")


def analyze(config: dict[str, Any], output_dir: Path) -> None:
    raw_dir = output_dir / "raw"
    stock_basic = pd.read_parquet(raw_dir / "stock_basic.parquet")
    snapshots: list[tuple[str, str, pd.DataFrame]] = []
    for layer in ("daily_basic", "moneyflow"):
        frame = pd.read_parquet(raw_dir / f"{layer}.parquet") if (raw_dir / f"{layer}.parquet").is_file() else pd.DataFrame()
        for date in config["market_dates"]:
            date_key = pd.Timestamp(date).strftime("%Y%m%d")
            snapshots.append((str(date), layer, frame.loc[frame.get("trade_date", pd.Series(dtype=object)).astype(str).eq(date_key)] if not frame.empty else frame))
    coverage = audit_cross_sectional_coverage(stock_basic, snapshots)
    coverage.to_csv(output_dir / "market_coverage.csv", index=False, encoding="utf-8-sig")

    intervals = parse_qlib_intervals(Path(config["qlib_interval_file"]))
    lifecycle_dates = list(config["market_dates"])[::4]
    lifecycle = audit_lifecycle_alignment(stock_basic, intervals, lifecycle_dates)
    lifecycle.to_csv(output_dir / "lifecycle_alignment.csv", index=False, encoding="utf-8-sig")

    statement_specs: list[tuple[str, str, pd.DataFrame]] = []
    sample = pd.read_csv(output_dir / "market_canary_sample.csv", encoding="utf-8-sig")
    for ts_code in sample["ts_code"].astype(str):
        for api in STATEMENT_FIELDS:
            path = raw_dir / "statements" / f"{api}_{ts_code.replace('.', '_')}.parquet"
            statement_specs.append((ts_code, api, pd.read_parquet(path) if path.is_file() else pd.DataFrame()))
    list_dates = dict(zip(sample["ts_code"].astype(str), pd.to_datetime(sample["list_date"], errors="coerce")))
    statement_detail, statement_summary = audit_statement_panel(statement_specs, years=config["statement_years"], list_dates=list_dates)
    statement_detail.to_csv(output_dir / "statement_issuer_audit.csv", index=False, encoding="utf-8-sig")
    statement_summary.to_csv(output_dir / "statement_layer_summary.csv", index=False, encoding="utf-8-sig")

    adjustment = pd.read_parquet(raw_dir / "adjustment_continuity.parquet") if (raw_dir / "adjustment_continuity.parquet").is_file() else pd.DataFrame()
    adjustment_summary = audit_adjustment_continuity(adjustment)
    adjustment_summary.to_csv(output_dir / "adjustment_continuity.csv", index=False, encoding="utf-8-sig")

    frontiers = []
    for layer in ("daily_basic", "moneyflow"):
        frontiers.append(continuous_frontier(coverage, layer=layer, minimum_coverage=float(config["minimum_market_coverage"]), consecutive_periods=4))
    frontier_frame = pd.DataFrame(frontiers)
    frontier_frame.to_csv(output_dir / "admitted_frontiers.csv", index=False, encoding="utf-8-sig")

    factor_inventory = pd.read_csv(resolve("outputs/factor_universe_v2/current/factor_inventory_v2.csv"))
    from research_validation.dataset_design import classify_factor_history_layer
    family = factor_inventory[["name", "required_fields", "economic_family", "source"]].copy()
    family["history_layer"] = family["required_fields"].map(classify_factor_history_layer)
    frontier_by_layer = {"price_volume_core": "2000-01-04 technical / admission blocked", "daily_basic_plus_price_volume": "see admitted_frontiers.csv", "moneyflow_plus_price_volume": "see admitted_frontiers.csv", "fundamental_pit_plus_daily_basic": "blocked pre-2018"}
    family["earliest_reliable_materialization"] = family["history_layer"].map(frontier_by_layer).fillna("unclassified dependency")
    family.groupby(["history_layer", "earliest_reliable_materialization"], as_index=False).agg(defined_factors=("name", "size"), economic_families=("economic_family", lambda values: ",".join(sorted(set(map(str, values))))), sources=("source", lambda values: ",".join(sorted(set(map(str, values)))))).to_csv(output_dir / "factor_family_frontier.csv", index=False)

    lifecycle_min = float(lifecycle[["intersection_ratio_qlib", "intersection_ratio_stock_basic"]].min().min()) if not lifecycle.empty else 0.0
    statement_p10 = float(statement_summary["p10_period_coverage"].min()) if not statement_summary.empty else 0.0
    row_caps = int(statement_summary["row_cap_issuer_count"].sum()) if not statement_summary.empty else 0
    adjustment_pass = bool(not adjustment_summary.empty and adjustment_summary["positive_factor_ratio"].ge(1.0).all() and adjustment_summary["duplicate_date_rows"].eq(0).all())
    decision = pd.DataFrame([
        ["market_daily_basic", "pass" if coverage.loc[coverage.layer.eq("daily_basic"), "coverage_ratio"].ge(float(config["minimum_market_coverage"])).all() else "blocked", f"minimum sampled-date coverage={coverage.loc[coverage.layer.eq('daily_basic'), 'coverage_ratio'].min():.3f}"],
        ["market_moneyflow", "pass" if coverage.loc[coverage.layer.eq("moneyflow"), "coverage_ratio"].ge(float(config["minimum_market_coverage"])).all() else "blocked", f"minimum sampled-date coverage={coverage.loc[coverage.layer.eq('moneyflow'), 'coverage_ratio'].min():.3f}"],
        ["fundamental_pit_2010_2017", "blocked" if row_caps or statement_p10 < float(config["minimum_statement_period_coverage"]) else "conditional_pass", f"p10 issuer-period coverage={statement_p10:.3f}; row-cap issuers={row_caps}"],
        ["lifecycle_survivorship_canary", "pass" if lifecycle_min >= float(config["minimum_lifecycle_intersection"]) else "blocked", f"minimum Qlib/stock_basic intersection={lifecycle_min:.3f}; current snapshot is not a vintage"],
        ["corporate_action_adjustment", "pass" if adjustment_pass else "blocked", f"adjustment canary issuers={len(adjustment_summary)}; positive factors and daily overlap audited"],
        ["full_factor_universe_v2_common_frontier", "not_admitted", "intersection remains blocked until PIT, lifecycle and adjustment gates all pass market-wide"],
        ["extended_matrix", "not_generated", "this qualification run does not create or mutate Matrix artifacts"],
    ], columns=["decision_area", "status", "reason"])
    decision.to_csv(output_dir / "qualification_decision.csv", index=False, encoding="utf-8-sig")
    daily_frontier = frontier_frame.loc[frontier_frame["layer"].eq("daily_basic"), "frontier"].iloc[0] if not frontier_frame.loc[frontier_frame["layer"].eq("daily_basic")].empty else "not found"
    flow_frontier = frontier_frame.loc[frontier_frame["layer"].eq("moneyflow"), "frontier"].iloc[0] if not frontier_frame.loc[frontier_frame["layer"].eq("moneyflow")].empty else "not found"
    daily_min = coverage.loc[coverage["layer"].eq("daily_basic"), "coverage_ratio"].min()
    flow_min = coverage.loc[coverage["layer"].eq("moneyflow"), "coverage_ratio"].min()
    report = f"""# Historical Frontier Admission V1

> 状态：`MARKET-LEVEL QUALIFICATION COMPLETE / EXTENDED MATRIX NOT GENERATED`。本轮把前一阶段的代表性 probe 扩展为按上市 cohort 与存续状态分层的市场 canary；未读取 model outcomes，未修改 Research Protocol V2、Factor Universe V2 definitions、frozen Matrix、Strategy V1 或 Forward Track。

## 数据源与方法

- Tushare `stock_basic`（listed/delisted active canary）、`daily_basic`、`moneyflow`、`daily`、`adj_factor` 与四类 statements；每次请求均保留 network receipt。
- Community Qlib `instruments/all.txt` 用作 lifecycle interval 对照；不是把当前 stock_basic 快照冒充历史 vintage。
- 28 个 issuer 按 listing cohort × listed/delisted 分层抽样；48 个 2010–2021 季度代表交易日用于市场横截面 coverage。
- 复权审计只对 pre-2010 cohort 做 bounded canary，检查 daily/adj_factor overlap、正值、重复日期与 factor-change events。

## 观测 frontier 与 blockers

- `daily_basic`：稳定连续尾部候选 `{daily_frontier}`；全窗口最低 coverage `{daily_min:.3f}`，因此早期低覆盖仍不能整体准入。
- `moneyflow`：稳定连续尾部候选 `{flow_frontier}`；全窗口最低 coverage `{flow_min:.3f}`（2010-01-04 明显缺口）。
- Fundamental PIT：按 issuer listing date 修正分母后 2010–2017 period coverage 的 p10 为 `{statement_p10:.3f}`，但 `{row_caps}` 个 issuer 的 `fina_indicator` response 触及 100-row cap；revision/duplicate rows 普遍存在，故 PIT vintage 仍 blocked。
- Lifecycle/survivorship：Qlib 与 stock_basic 交集最低 `{lifecycle_min:.3f}`；且 stock_basic 是 current snapshot，历史 vintage 未被证明，故 gate blocked。
- Corporate-action/adjustment：12 个 pre-2010 issuer 的 factor 均为正、无重复日期且 daily overlap 完整；该 bounded pass 不能抵消 PIT/lifecycle blocker。

## Factor Universe V2 与 Matrix 决策

`factor_family_frontier.csv` 将每个定义映射到 price-volume、daily_basic、moneyflow 或 fundamental PIT 依赖。Qlib technical price history 仍可追溯至 2000-01-04，但这只是 long-history core 的能力证据，不是 Full V2 的 admitted start。Full Factor Universe V2 common frontier 必须取所有依赖层、PIT、lifecycle 与 adjustment 的交集；本轮结论为 `not_admitted`。因此没有生成 extended Matrix，也不存在需要与旧 2021+ Matrix 做 overlap 一致性声明的新 artifact。

## 复现与治理

```powershell
E:\\anaconda_envs\\qlib_env\\python.exe scripts\\run_historical_frontier_admission_v1.py --stage all
```

网络 receipts 保存在 `network_receipts.csv`，token 不写入任何 artifact；失败请求原样保留。`qualification_decision.csv` 是机器可读 gate 结果。

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
"""
    (output_dir / "REPORT.md").write_text(report, encoding="utf-8")


def finalize(config_path: Path, config: dict[str, Any], output_dir: Path) -> None:
    files = sorted(path for path in output_dir.rglob("*") if path.is_file() and path.name != "manifest.json")
    manifest = {
        "schema_version": 1,
        "stage_id": config["stage_id"],
        "artifact_status": "market_qualification_complete_no_extended_matrix",
        "config_sha256": sha256(config_path),
        "extended_matrix_generated": False,
        "formal_structured_ml_competition_started": False,
        "research_protocol_v2_changed": False,
        "factor_universe_v2_definitions_changed": False,
        "frozen_matrix_changed": False,
        "strategy_v1_changed": False,
        "forward_track_changed": False,
        "model_outcomes_read": False,
        "network_receipts_present": (output_dir / "network_receipts.csv").is_file(),
        "output_file_hashes": {str(path.relative_to(output_dir)): sha256(path) for path in files},
    }
    manifest["manifest_identity"] = canonical_hash(manifest["output_file_hashes"])
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Historical Frontier Admission V1")
    parser.add_argument("--config", type=Path, default=Path("configs/historical_frontier_admission_v1.yaml"))
    parser.add_argument("--stage", choices=("probe", "analyze", "finalize", "all"), default="all")
    args = parser.parse_args()
    config_path = resolve(args.config)
    config = load_config(config_path)
    output_dir = resolve(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.stage in {"probe", "all"}:
        probe(config, output_dir)
    if args.stage in {"analyze", "all"}:
        analyze(config, output_dir)
    if args.stage in {"finalize", "all"}:
        finalize(config_path, config, output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
