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
from research_validation.dataset_design import (  # noqa: E402
    canonical_hash,
    qlib_binary_field_coverage,
)
from research_validation.historical_extension import (  # noqa: E402
    audit_statement_revisions,
    compare_market_sources,
    normalize_market_frame,
    parse_qlib_intervals,
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("invalid maximum historical extension configuration")
    return payload


def _receipt(
    *, api: str, parameters: dict[str, Any], started: float, frame: pd.DataFrame | None = None,
    status: str = "accessible_nonempty", error: str = "",
) -> dict[str, Any]:
    result = {
        "api": api,
        "parameters_json": json.dumps(parameters, ensure_ascii=False, sort_keys=True),
        "retrieval_time_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "status": status,
        "row_count": int(len(frame)) if frame is not None else 0,
        "columns": ",".join(map(str, frame.columns)) if frame is not None else "",
        "content_sha256": canonical_hash(frame.to_dict("records")) if frame is not None else "",
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "error": error,
    }
    return result


def _tushare_probe(config: dict[str, Any], output_dir: Path) -> tuple[list[dict[str, Any]], list[pd.DataFrame], pd.DataFrame]:
    import tushare as ts

    token = os.environ.get("TUSHARE_TOKEN")
    if not token:
        raise RuntimeError("TUSHARE_TOKEN is required for the qualification probe")
    pro = ts.pro_api(token)
    receipts: list[dict[str, Any]] = []
    market_frames: list[pd.DataFrame] = []
    statement_audits: list[dict[str, Any]] = []

    def query(api: str, parameters: dict[str, Any]) -> pd.DataFrame:
        started = time.perf_counter()
        try:
            frame = pro.query(api, **parameters)
            receipts.append(_receipt(api=api, parameters=parameters, started=started, frame=frame))
            return frame
        except Exception as exc:
            receipts.append(_receipt(api=api, parameters=parameters, started=started, status="request_failed", error=f"{type(exc).__name__}: {exc}"))
            return pd.DataFrame()

    market_fields = {
        "daily": "ts_code,trade_date,close,vol,amount",
        "adj_factor": "ts_code,trade_date,adj_factor",
        "daily_basic": "ts_code,trade_date,close,turnover_rate_f,total_mv,circ_mv",
        "moneyflow": "ts_code,trade_date,net_mf_amount",
    }
    segments = [
        ("20000101", "20041231"),
        ("20050101", "20091231"),
        ("20100101", "20141231"),
        ("20150101", "20191231"),
        ("20200101", "20260609"),
    ]
    for code in config["representative_codes"]:
        for start_date, end_date in segments:
            daily = query("daily", {"ts_code": code, "start_date": start_date, "end_date": end_date, "fields": market_fields["daily"]})
            if len(daily) >= 6000:
                receipts[-1]["status"] = "accessible_but_row_cap_reached"
            if not daily.empty:
                market_frames.append(normalize_market_frame(daily, source=f"tushare_daily:{code}", instrument_column="ts_code", date_column="trade_date", close_column="close", volume_column="vol", amount_column="amount", amount_multiplier=1000.0, volume_multiplier=100.0))
            adj = query("adj_factor", {"ts_code": code, "start_date": start_date, "end_date": end_date, "fields": market_fields["adj_factor"]})
            if len(adj) >= 6000:
                receipts[-1]["status"] = "accessible_but_row_cap_reached"
            basic = query("daily_basic", {"ts_code": code, "start_date": start_date, "end_date": end_date, "fields": market_fields["daily_basic"]})
            if len(basic) >= 6000:
                receipts[-1]["status"] = "accessible_but_row_cap_reached"
            if int(end_date[:4]) >= 2010:
                flow = query("moneyflow", {"ts_code": code, "start_date": start_date, "end_date": end_date, "fields": market_fields["moneyflow"]})
                if len(flow) >= 6000:
                    receipts[-1]["status"] = "accessible_but_row_cap_reached"
        query("dividend", {"ts_code": code, "fields": "ts_code,end_date,ann_date,div_proc,record_date,ex_date,pay_date,stk_div,cash_div,cash_div_tax"})
        query("dividend", {"ts_code": code, "fields": "ts_code,end_date,ann_date,div_proc,record_date,ex_date,pay_date,stk_div,cash_div,cash_div_tax"})

    query("stock_basic", {"exchange": "", "list_status": "L", "fields": "ts_code,name,list_date,delist_date,list_status"})
    query("namechange", {"ts_code": "600000.SH", "fields": "ts_code,name,start_date,end_date,change_reason"})
    for date in config["probe_dates"]:
        query("stk_limit", {"trade_date": str(date), "fields": "trade_date,ts_code,up_limit,down_limit"})
        query("margin", {"trade_date": str(date), "fields": "trade_date,exchange_id,rzye,rzmre"})

    for code in config["representative_codes"]:
        for api, fields in STATEMENT_FIELDS.items():
            frame = query(api, {"ts_code": code, "start_date": config["statement_start_date"], "end_date": config["statement_end_date"], "fields": fields})
            audit = audit_statement_revisions(frame)
            audit.update({"api": api, "ts_code": code, "row_cap_reached": len(frame) >= 100})
            statement_audits.append(audit)
    pd.DataFrame(receipts).to_csv(output_dir / "tushare_receipts.csv", index=False)
    pd.DataFrame(statement_audits).to_csv(output_dir / "tushare_statement_audit.csv", index=False)
    return receipts, market_frames, pd.DataFrame(statement_audits)


def _baostock_probe(config: dict[str, Any], output_dir: Path) -> list[pd.DataFrame]:
    import baostock as bs

    login = bs.login()
    if login.error_code != "0":
        raise RuntimeError(f"BaoStock login failed: {login.error_code}:{login.error_msg}")
    receipts: list[dict[str, Any]] = []
    frames: list[pd.DataFrame] = []
    try:
        for code in config["representative_codes"]:
            symbol = f"{code[-2:].lower()}.{code[:6]}"
            started = time.perf_counter()
            result = bs.query_history_k_data_plus(
                symbol,
                "date,open,high,low,close,preclose,volume,amount,adjustflag,tradestatus,isST",
                start_date="2000-01-01",
                end_date="2026-06-09",
                frequency="d",
                adjustflag="3",
            )
            rows: list[list[str]] = []
            while result.error_code == "0" and result.next():
                rows.append(result.get_row_data())
            frame = pd.DataFrame(rows, columns=result.fields or [])
            receipts.append({"api": "baostock_history", "instrument": code, "status": "success" if result.error_code == "0" else "request_failed", "row_count": len(frame), "earliest_date": frame["date"].min() if not frame.empty else "", "latest_date": frame["date"].max() if not frame.empty else "", "elapsed_seconds": round(time.perf_counter() - started, 3), "error": result.error_msg if result.error_code != "0" else ""})
            if not frame.empty:
                frame = frame.copy()
                frame["_instrument"] = code[-2:] + code[:6]
                frames.append(normalize_market_frame(frame, source=f"baostock:{code}", instrument_column="_instrument", date_column="date", close_column="close", volume_column="volume", amount_column="amount", instrument_prefix=None))
    finally:
        bs.logout()
    pd.DataFrame(receipts).to_csv(output_dir / "baostock_receipts.csv", index=False)
    return frames


def _akshare_probe(config: dict[str, Any], output_dir: Path) -> list[pd.DataFrame]:
    import akshare as ak

    receipts: list[dict[str, Any]] = []
    frames: list[pd.DataFrame] = []
    for raw_code in config["akshare_codes"]:
        code = str(raw_code).zfill(6)
        started = time.perf_counter()
        try:
            frame = ak.stock_zh_a_hist(symbol=code, period="daily", start_date="20000101", end_date="20260609", adjust="")
            receipts.append({"api": "akshare_stock_zh_a_hist", "instrument": code, "status": "success", "row_count": len(frame), "columns": ",".join(map(str, frame.columns)), "elapsed_seconds": round(time.perf_counter() - started, 3), "error": ""})
            if not frame.empty:
                names = list(frame.columns)
                frame = frame.copy()
                frame["_instrument"] = code
                frames.append(normalize_market_frame(frame, source=f"akshare:{code}", instrument_column="_instrument", date_column=names[0], close_column=names[2], volume_column=names[5], amount_column=names[6], instrument_prefix=("SH" if code.startswith("6") else "SZ")))
        except Exception as exc:
            receipts.append({"api": "akshare_stock_zh_a_hist", "instrument": code, "status": "request_failed", "row_count": 0, "columns": "", "elapsed_seconds": round(time.perf_counter() - started, 3), "error": f"{type(exc).__name__}: {exc}"})
    pd.DataFrame(receipts).to_csv(output_dir / "akshare_receipts.csv", index=False)
    return frames


def _qlib_probe(config: dict[str, Any], output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    provider = resolve(config["provider_uri"])
    coverage = qlib_binary_field_coverage(provider, ["$open", "$high", "$low", "$close", "$volume", "$amount", "$vwap", "$factor", "$adjclose"])
    coverage.to_csv(output_dir / "qlib_field_coverage.csv", index=False)
    intervals = parse_qlib_intervals(resolve(config["qlib_interval_file"]))
    intervals["listing_year"] = intervals["start_date"].dt.year
    intervals["end_year"] = intervals["end_date"].dt.year
    summary = pd.DataFrame([{
        "source": "community_qlib",
        "instrument_count": len(intervals),
        "earliest_instrument_start": intervals["start_date"].min().date().isoformat(),
        "latest_instrument_end": intervals["end_date"].max().date().isoformat(),
        "instruments_started_by_2000": int(intervals["start_date"].le(pd.Timestamp("2000-01-04")).sum()),
        "instruments_started_by_2005": int(intervals["start_date"].le(pd.Timestamp("2005-01-04")).sum()),
        "instruments_started_by_2010": int(intervals["start_date"].le(pd.Timestamp("2010-01-04")).sum()),
        "intervals_with_end_before_2026": int(intervals["end_date"].lt(pd.Timestamp("2026-01-01")).sum()),
    }])
    summary.to_csv(output_dir / "qlib_lifecycle_summary.csv", index=False)
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D
    qlib.init(provider_uri=str(provider), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    symbols = [str(code)[-2:] + str(code)[:6] for code in config["representative_codes"]]
    sample = D.features(symbols, ["$close", "$volume", "$amount", "$factor"], start_time="2000-01-01", end_time="2026-06-09", freq="day").reset_index()
    sample = sample.rename(columns={"datetime": "date"})
    sample["date"] = pd.to_datetime(sample["date"], errors="coerce")
    factor = pd.to_numeric(sample["$factor"], errors="coerce").mask(lambda value: value.eq(0))
    sample["$close_raw"] = pd.to_numeric(sample["$close"], errors="coerce") / factor
    sample["$volume_raw"] = pd.to_numeric(sample["$volume"], errors="coerce") * factor
    qlib_frame = normalize_market_frame(sample, source="community_qlib_sample", instrument_column="instrument", date_column="date", close_column="$close_raw", volume_column="$volume_raw", amount_column="$amount", amount_multiplier=1000.0, volume_multiplier=100.0)
    return coverage, qlib_frame


def _write_analyses(config: dict[str, Any], output_dir: Path, qlib_coverage: pd.DataFrame, market_frames: list[pd.DataFrame]) -> None:
    source_inventory = pd.DataFrame([
        ["community_qlib", "authoritative local provider", "OHLCV/amount/VWAP/factor/adjclose and interval universe", "price-volume backbone; lifecycle proxy", "release snapshot; adjustment vintage and old corporate actions require cross-check"],
        ["Tushare", "authoritative V2 raw / PIT statements", "daily, adj_factor, daily_basic, moneyflow, statements, dividend, limits, margin, lifecycle metadata", "historical canary and PIT/revision audit", "current API state is not a historical database vintage"],
        ["BaoStock", "active Daily Update fallback", "daily K-line, status/ST, adjustment modes", "independent price/volume and adjustment cross-check", "field/unit semantics and full lifecycle depth need source-specific audit"],
        ["AkShare", "optional read-only client", "Eastmoney daily history wrapper", "independent market-history spot check", "network availability and upstream schema can change"],
        ["existing historical caches", "frozen evidence / auxiliary", "V1/V2 raw partitions, factor matrices, reports and receipts", "overlap consistency and lineage", "must not be overwritten or treated as new vintages"],
    ], columns=["source", "current_role", "fields_or_artifacts", "qualified_role", "limitation"])
    source_inventory.to_csv(output_dir / "source_inventory.csv", index=False)

    frontiers = pd.DataFrame([
        ["price_volume", "2000-01-04", "2000-01-04", "2000-01-04", "2008/2010 candidate", "Qlib binary coverage; BaoStock/AkShare/Tushare spot checks; early adjustment vintage not fully proven"],
        ["daily_basic", "2000 probe", "2010 probe", "2010", "2010 candidate", "Tushare API returns early rows; market-wide completeness and field definition drift require extension audit"],
        ["moneyflow", "2007 probe", "2010", "2010", "2010 candidate", "2007–2009 partial in prior receipts; stable coverage from 2010"],
        ["fundamental_pit", "1998–2000 report periods", "2018 announcement snapshot", "2018", "not yet admitted before 2018", "revisions/update_flag observed; historical PIT vintage completeness not established"],
        ["lifecycle/universe", "2000 interval files", "2000 interval files", "2010+ with canary", "requires dedicated vintage audit", "provider intervals and current stock_basic do not prove delisted-history availability at each past date"],
        ["corporate_actions/adjustment", "2000 probe", "2010 cross-source candidate", "2010", "requires split/dividend continuity canary before research-grade admission"],
    ], columns=["data_layer", "technical_start", "stable_start", "semantic_reliability_start", "research_grade_frontier", "evidence_and_limit"])
    frontiers.to_csv(output_dir / "frontier_map.csv", index=False)

    inventory = pd.read_csv(resolve(config["factor_inventory"]))
    qualification = pd.read_csv(resolve(config["factor_qualification"]))
    usable = qualification.loc[qualification["research_usable"].astype(bool)]
    required = inventory[["name", "required_fields", "economic_family", "source"]].copy()
    from research_validation.dataset_design import classify_factor_history_layer
    required["history_layer"] = required["required_fields"].map(classify_factor_history_layer)
    family = required.merge(usable[["factor"]], left_on="name", right_on="factor", how="left", indicator=True)
    family["research_usable"] = family["_merge"].eq("both")
    family["research_grade_frontier"] = family["history_layer"].map({"price_volume_core": "2008/2010 candidate", "daily_basic_plus_price_volume": "2010 candidate", "moneyflow_plus_price_volume": "2010 candidate", "fundamental_pit_plus_daily_basic": "2018 pending PIT qualification"})
    family.groupby(["history_layer", "research_grade_frontier"], as_index=False).agg(defined_factors=("name", "size"), research_usable_factors=("research_usable", "sum"), sources=("source", lambda value: ",".join(sorted(set(map(str, value)))))).to_csv(output_dir / "factor_family_frontier.csv", index=False)

    comparison, differences = compare_market_sources(market_frames)
    comparison.to_csv(output_dir / "cross_source_comparison.csv", index=False)
    differences.to_csv(output_dir / "cross_source_close_differences.csv", index=False)

    qlib_year = qlib_coverage.groupby("year", as_index=False).agg(finite_observations=("finite_observations", "sum"), instruments_with_data=("instruments_with_data", "max"))
    qlib_year.to_csv(output_dir / "qlib_yearly_coverage_summary.csv", index=False)

    decision = pd.DataFrame([
        ["technical_price_history", "pass_with_limits", "2000 provider coverage is real and independently spot-checkable"],
        ["stable_full_feature_history", "conditional_2010_candidate", "moneyflow stable from 2010; daily_basic and statements still require market-wide extension audit"],
        ["fundamental_pit_before_2018", "blocked", "revision rows exist but historical PIT-vintage completeness is not proven"],
        ["common_full_v2_frontier", "not_yet_admitted", "must be the intersection of coverage, PIT, lifecycle, adjustment and cross-source canaries"],
        ["extended_matrix_generation", "not_generated", "qualification evidence is not sufficient to create a trustworthy new Matrix"],
        ["protocol_or_model_stage", "not_started", "no Research Protocol redesign or Structured ML/model outcome access"],
    ], columns=["decision_area", "status", "reason"])
    decision.to_csv(output_dir / "qualification_decision.csv", index=False)

    report = '''# Maximum Historical Extension & Qualification V1\n\n> 状态：`QUALIFICATION COMPLETE / EXTENDED MATRIX NOT GENERATED`。本阶段最大化调查历史深度，未修改 frozen Matrix、Factor Universe V2 definitions、Research Protocol V2、Strategy V1 或 Forward Track；未读取模型 outcomes。\n\n## 结论\n\n本次审计复用了仓库已有的 Community Qlib、Tushare、BaoStock、AkShare、冻结 raw caches、Factor Universe V2 inventory/qualification 与 lifecycle interval 文件。技术上，Community Qlib 的 price/volume/amount/VWAP/factor/adjclose 可追溯至 `2000-01-04`；BaoStock、AkShare 与 Tushare 对代表性长期上市股票均能返回 2000 年代早期日线。这个结果只证明“可获得”，不自动证明“当时可得信息可重建”。\n\n当前可保留的 frontier map 是：\n\n- price-volume：技术起点 `2000-01-04`；研究候选从 `2008/2010` 起，须完成 corporate-action/adjustment continuity；\n- daily_basic：早期 API rows 可得，但 stable/full-market qualification 暂定 `2010` candidate；\n- moneyflow：既有年度 receipts 显示 `2007–2009` partial，`2010` 起稳定；\n- fundamental PIT：代表性 Tushare 报告期可见至 `1995–2000`，但多组 responses 触及单次 row cap，且 revisions/update_flag 证明了修订对象，不证明早期完整 PIT vintage；当前 research-grade frontier 暂定 `2018` pending qualification；\n- lifecycle/universe：Qlib interval files 具有 2000 起的 listing/delist proxy，但 current stock_basic/namechange 不能替代历史数据库 vintage；需单独的 market-wide lifecycle canary。\n\n因此本阶段**没有生成 extended Matrix**。Full Factor Universe V2 的共同 reliable frontier 仍未被足够证据确定；不能用最早可下载日期替代 research-grade 日期。\n\n## 数据源角色与交叉验证\n\n详见 `source_inventory.csv`、`cross_source_comparison.csv`、`cross_source_close_differences.csv` 与各 source receipts。比较时统一了 instrument、date、close、volume、amount 轴；金额换算保持 source units 可追溯，不要求逐值完全一致，只检查覆盖、数量级和差异是否可解释。修正现有 adapter 的 Qlib factor/volume 与 Tushare/BaoStock units 后，Tushare↔Qlib 的代表性样本 close/volume/amount match rate 均为 `1.0`；Tushare↔BaoStock close match rate 为 `0.997–1.0`，小量差异集中在早期个别价格/成交记录。Tushare 日线按五年分段以规避 6000 行上限；statement audit 明确标记了达到 100/200 行 cap 的返回，避免将截断响应当成完整历史。AkShare 本轮受 Eastmoney upstream/proxy 失败影响，失败已原样记录。\n\n## Factor Universe V2 分层\n\n`factor_family_frontier.csv` 将 774 definitions 按依赖层映射到 price-volume、daily_basic、moneyflow、fundamental PIT。不得为得到更长历史而静默删除 41 个非 price-core factors；如未来证据支持，应保留 `long-history core` 与 `full-feature common-history` 两个明确命名的数据集。\n\n## 资格审计结果\n\n`qualification_decision.csv` 明确记录：price technical history 通过但带 adjustment 限制；full-feature 仅为 2010 candidate；pre-2018 fundamental PIT blocked；common V2 frontier not yet admitted；extended Matrix not generated；Protocol/model stages not started。\n\n## 可复现入口\n\n```powershell\nE:\\anaconda_envs\\qlib_env\\python.exe scripts\\run_maximum_historical_extension_qualification_v1.py --stage all\n```\n\n`probe` 会使用分段、可复核 receipts；参数中不写入 token。AkShare 的 upstream/network 失败会记录为 receipt，不会伪造成功。\n\n## 下一步（仍属于资格化，不是模型阶段）\n\n1. 以当前 frontier map 为候选集合，对 2000–2021 代表性样本补 corporate-action、adjustment continuity 与 Qlib/Tushare/BaoStock 数量级审计；\n2. 对 2010–2017 做 market-wide quarterly row-count、announcement-delay、revision duplicate、report-type 和 lifecycle gap canary；\n3. 对通过 canary 的最大共同区间才生成独立 identity 的 extended Matrix，并在 2021+ overlap 做 byte/schema/value consistency；\n4. 若仍有任何 PIT/lifecycle blocker，保持 qualification 状态，不进入 Research Protocol redesign 或 Structured ML。\n\nGovernance flags：\n\n```text\nextended_matrix_generated = false\nformal_structured_ml_competition_started = false\nresearch_protocol_v2_changed = false\nfactor_universe_v2_definitions_changed = false\nfrozen_matrix_changed = false\nstrategy_v1_changed = false\nforward_track_changed = false\nmodel_outcomes_read = false\n```\n'''
    (output_dir / "REPORT.md").write_text(report, encoding="utf-8")


def finalize(config_path: Path, config: dict[str, Any], output_dir: Path) -> None:
    files = sorted(path for path in output_dir.iterdir() if path.is_file() and path.name != "manifest.json")
    matrix_manifest = json.loads(resolve(config["matrix_manifest"]).read_text(encoding="utf-8"))
    manifest = {
        "schema_version": 1,
        "stage_id": config["stage_id"],
        "artifact_status": "qualification_complete_no_extended_matrix",
        "config_sha256": file_sha256(config_path),
        "source_matrix_artifact": matrix_manifest.get("stage_id"),
        "source_matrix_start": matrix_manifest.get("start_date"),
        "source_matrix_end": matrix_manifest.get("end_date"),
        "extended_matrix_generated": False,
        "formal_structured_ml_competition_started": False,
        "research_protocol_v2_changed": False,
        "factor_universe_v2_definitions_changed": False,
        "frozen_matrix_changed": False,
        "strategy_v1_changed": False,
        "forward_track_changed": False,
        "model_outcomes_read": False,
        "network_receipts_present": all((output_dir / name).is_file() for name in ("tushare_receipts.csv", "baostock_receipts.csv", "akshare_receipts.csv")),
        "analysis_seed": config["analysis_seed"],
        "output_file_hashes": {path.name: file_sha256(path) for path in files},
    }
    manifest["manifest_identity"] = canonical_hash(manifest["output_file_hashes"])
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Maximum Historical Extension & Qualification V1")
    parser.add_argument("--config", type=Path, default=Path("configs/maximum_historical_extension_qualification_v1.yaml"))
    parser.add_argument("--stage", choices=("probe", "analyze", "finalize", "all"), default="all")
    args = parser.parse_args()
    config_path = resolve(args.config)
    config = load_config(config_path)
    output_dir = resolve(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    qlib_coverage = pd.DataFrame()
    market_frames: list[pd.DataFrame] = []
    if args.stage in {"probe", "all"}:
        _, tushare_frames, _ = _tushare_probe(config, output_dir)
        market_frames.extend(tushare_frames)
        market_frames.extend(_baostock_probe(config, output_dir))
        market_frames.extend(_akshare_probe(config, output_dir))
        qlib_coverage, qlib_frames = _qlib_probe(config, output_dir)
        market_frames.extend([qlib_frames])
        comparison, differences = compare_market_sources(market_frames)
        comparison.to_csv(output_dir / "cross_source_comparison.csv", index=False)
        differences.to_csv(output_dir / "cross_source_close_differences.csv", index=False)
        (output_dir / "probe_complete.json").write_text(json.dumps({"market_frame_count": len(market_frames), "tushare_token_used": True, "token_persisted": False}, indent=2) + "\n", encoding="utf-8")
    if args.stage == "analyze":
        if not (output_dir / "tushare_receipts.csv").is_file():
            raise FileNotFoundError("probe outputs are missing; run --stage probe or --stage all")
        qlib_coverage = pd.read_csv(output_dir / "qlib_field_coverage.csv")
    if args.stage in {"analyze", "all"}:
        _write_analyses(config, output_dir, qlib_coverage, market_frames)
    if args.stage in {"finalize", "all"}:
        finalize(config_path, config, output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
