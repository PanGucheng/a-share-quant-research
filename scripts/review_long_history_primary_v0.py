"""Append descriptive review recommendations to frozen Primary V0 evidence."""
from pathlib import Path
import hashlib
import json
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/long_history_multi_evaluator_screening_v1"
OUT = REPORT / "review_v0"
FLAGS = ["direction_instability", "regime_concentrated", "low_sample_coverage", "by_sensitivity_not_significant"]
SPECIAL = {
    "mature_log_total_market_cap": "规模暴露观察项：负向选择等于偏小市值；C时期反向且BY不显著，暂缓作为稳定Alpha。",
    "mature_amihud_illiquidity_20": "正方向偏向更不流动的股票；存在反向时期，优先检查容量和流动性暴露。",
    "mature_book_to_market_pit": "保留价值研究线索；C时期均值接近零且有4个反向年度，不应标成全时期稳定；与book_to_price概念重叠但口径不同。",
    "mature_book_to_price": "保留价值研究线索；C时期均值接近零且有4个反向年度；与PIT账面市值比核对时点和分母口径。",
    "mature_earnings_to_price_pit": "保留估值研究线索；与earnings_yield_ttm的会计窗口不同，不按本轮表现选口径。",
    "mature_earnings_yield_ttm": "与PIT盈利市值比不等同；正PE限制改变样本，先解释五桶形态差异。",
    "mature_idiosyncratic_volatility_60": "负方向低残差波动效应；优先作为风险暴露/Alpha两种解释的对照项，未证明独立增量。",
    "mature_reversal_1m": "正方向已内置反转；21日定义与ret_20和ROC20窗口不同，按反转家族比较，不能直接视为独立信号。",
    "ret_20": "负方向即20日反转；与ROC20/CLOSE20在正价格条件下为单调反向变换，但实际缺失样本/计算精度仍需核对。",
    "rev_20_exclude_5": "保留排除最近5日的反转研究线索；相对普通反转的增量尚未检验。",
    "mature_dividend_yield_ttm": "68.37%有效样本覆盖且加权收益年度一致性未过线；暂缓升级，需核对缺失/零股息口径。",
    "mature_sales_to_price_pit": "加权收益年度一致性未过线；与TTM版本都仅2/3，不为得到3/3更换会计窗口。",
    "mature_sales_to_price_ttm": "加权收益年度一致性未过线；BY q约0.05007，保持原标注，不按显示舍入改判。",
    "ta_trend_adx_pos": "有效样本覆盖约35%；早年覆盖极稀，暂缓升级，先解释可用样本随时期的变化。",
    "ta_trend_adx_neg": "有效样本覆盖约35%；早年覆盖极稀，暂缓升级，先解释可用样本随时期的变化。",
    "ta_volatility_atr": "绝对价格单位的波幅兼有低覆盖和反向时期；不能直接当作稳定低波Alpha。",
    "ta_trend_psar_down": "下降状态下的PSAR价格线，缺失可能包含状态定义；不能简单插补为连续全市场因子。",
    "ta_trend_kst": "现有低覆盖标注；各Era方向一致并不能排除样本构成影响，保留待覆盖解释。",
    "ta_trend_kst_sig": "覆盖略低于冻结80%标注线；不因接近阈值改标，补充年度覆盖解释。",
    "ta_volatility_bbhi": "源代码为突破布林上轨的0/1指标；五分桶结构不适用。保留事件/状态研究线索，缺少分组样本与事件收益检验。",
    "ta_volatility_kchi": "源代码为突破肯特纳上轨的0/1指标；五分桶结构不适用。保留事件/状态研究线索，缺少分组样本与事件收益检验。",
    "kunquant_alpha101_alpha071": "时间序列秩的max组合；五桶均不可定义与并列值结构相容，但本轮未逐日核对唯一值分布。保留专项诊断。",
    "kunquant_alpha101_alpha005": "VWAP代理版本3/3而direct-VWAP版本0/3；属于不同语义，不按绩效偏好代理版本。",
    "kunquant_alpha101_alpha041": "VWAP代理版本3/3而direct-VWAP版本0/3；原始版本负方向，规范字段版本正方向，优先语义核查。",
    "kunquant_alpha101_alpha042": "与direct-VWAP版本同为3/3但数值和时期表现不同；不作为两份独立确认。",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def annotate(row):
    flags = [name for name in FLAGS if row[name]]
    if row.agreement == "3/3":
        category = "保留研究价值_待去重与暴露检查" if not flags else "有条件保留_暂缓升级"
    elif row.agreement == "2/3":
        category = "保留分歧审阅"
    elif row.agreement == "1/3":
        category = "降低连续Alpha研究优先级"
    elif row.agreement == "0/3":
        category = "当前20D候选研究不优先推进"
    else:
        category = "保留结构专项审阅" if row.pass_count else "证据不完整且现有规则不支持优先推进"
    notes = []
    name = row.factor
    group = re.sub(r"\d+$", "", name) if row.source in ("alpha158", "alpha360") else row.economic_subfamily
    if name.startswith("alpha360_"):
        notes.append("历史价格/成交量与当期值的比值序列；相邻lag与OHLC/VWAP列为结构相近线索，尚未计算数值冗余。")
        if not name.startswith("alpha360_VOLUME"):
            notes.append("正方向历史价格/当前收盘价可体现反转，不能仅按PriceTrend标签解释为追涨。")
        else:
            notes.append("滞后量/当前量的极端值可能影响数值加权；Rank IC与Pearson/加权收益分歧只作原因假设。")
    if name.startswith("alpha158_BETA"):
        notes.append("实际公式为Slope(close,n)/close，是价格斜率，不是市场回归Beta；原经济分类仅保留为历史元数据。")
    if row.source == "ta" and any(t in name for t in ["_ema_", "_sma_", "_ichimoku_", "_bbh", "_bbm", "_dch", "_dcl", "_dcm", "_kcc", "_kch", "_kcl", "_vwap"]):
        if name not in {"ta_volatility_bbhi", "ta_volatility_bbli", "ta_volatility_kchi", "ta_volatility_kcli"}:
            notes.append("价格线/通道类：先核对量纲和价格水平暴露，原始横截面高低并不自动代表标准化技术形态。")
    if row.economic_family == "Liquidity":
        notes.append("流动性/交易活跃度也可充当风险或条件变量；费用、规模中性化与容量均未验证。")
    if row.economic_family == "VolatilityRisk":
        notes.append("需区分风险暴露与独立Alpha；家族名不能替代公式审查。")
    if "proxy_to_canonical_replacement" in row.legacy_duplicate_relations:
        notes.append("存在VWAP代理/direct-VWAP语义对应项；保留双方身份，不以本轮绩效决定规范定义。")
    if name in SPECIAL:
        notes.append(SPECIAL[name])
    if not notes:
        notes.append("按冻结原生指标审阅；经济解释暂沿用描述性元数据，尚未证实独立增量或交易价值。")
    years = json.loads(row.annual_ic_sequence_raw)
    opposite = [y for y, value in years.items() if pd.notna(value) and value * row.analysis_direction < 0]
    return category, group, ";".join(flags) or "none_of_four_existing_flags", ";".join(opposite), " ".join(notes)


def main():
    manifest = json.loads((REPORT / "PRIMARY_V0_MANIFEST.json").read_text(encoding="utf-8"))
    for name in ("candidate_board.csv", "factor_evidence_board.csv", "factor_inventory.csv"):
        expected = manifest["file_hashes"][f"reports/long_history_multi_evaluator_screening_v1/{name}"]
        assert digest(REPORT / name) == expected, name
    board = pd.read_csv(REPORT / "candidate_board.csv", float_precision="round_trip")
    inventory = pd.read_csv(REPORT / "factor_inventory.csv")
    assert len(board) == board.factor.nunique() == 765
    assert set(board.factor) == set(inventory.loc[inventory.research_usable, "factor"])
    columns = ["factor", "source", "canonical_factor_id", "economic_family", "economic_subfamily", "agreement", "pass_count",
               "analysis_direction", "qlib_ic__mean", "annual_direction_agreement", "worst_directional_era_mean", "fdr_by_q_value",
               "ic_sample_coverage", "quantile_dates", "alphalens_quantile_monotonicity_raw",
               *[f"alphalens_q{i}__mean" for i in range(1, 6)], *[f"era_{e}_mean_raw" for e in "ABCD"],
               "alphalens_reasons", "jqfactor_reasons", "qlib_reasons", *FLAGS]
    review = board[columns].copy()
    review[["review_recommendation", "structural_group_hint", "existing_flags", "opposite_annual_periods", "review_notes"]] = pd.DataFrame(
        [annotate(r) for _, r in board.iterrows()], index=board.index)
    review["reviewer"] = "Codex_assisted_review"
    review["user_decision"] = "pending"
    review["scope"] = "2010_2023_primary_20d_descriptive_review_not_new_selection"
    review["basis_rule_id"] = manifest["rule_id"]
    review = review.sort_values("factor").reset_index(drop=True)
    out = OUT
    out.mkdir(parents=True, exist_ok=True)
    review.to_csv(out / "factor_review.csv", index=False, lineterminator="\n")
    inventory.loc[~inventory.research_usable].to_csv(out / "blocked_inventory.csv", index=False, lineterminator="\n")
    review.loc[review.factor.isin(SPECIAL)].to_csv(out / "targeted_cases.csv", index=False, lineterminator="\n")
    qlib = board.loc[board.source.isin(["alpha158", "alpha360"])].copy()
    qlib["expression"] = qlib.definition.str.extract(r"Qlib Alpha(?:158|360) expression: (.*)")[0].str.replace(" Alpha360 batch V4 passed.", "", regex=False)
    overlaps = []
    for formula, group in qlib.groupby("expression"):
        if len(group) > 1:
            overlaps.append({"expression": formula, "factors": ";".join(group.factor), "agreements": ";".join(group.agreement),
                             "evidence": "same_recorded_expression_not_full_raw_equality", "action": "retain_aliases_compare_before_representative_selection"})
    pd.DataFrame(overlaps).to_csv(out / "formula_overlap.csv", index=False, lineterminator="\n")
    by_name = board.set_index("factor")
    pairs = []
    for _, row in board.loc[board.factor.str.endswith("_canonical_vwap_v2")].iterrows():
        original = row.factor.removesuffix("_canonical_vwap_v2")
        if original in by_name.index:
            prior = by_name.loc[original]
            pairs.append({"proxy_factor": original, "direct_vwap_factor": row.factor, "proxy_agreement": prior.agreement,
                          "direct_agreement": row.agreement, "proxy_ic": prior.qlib_ic__mean, "direct_ic": row.qlib_ic__mean,
                          "proxy_direction": prior.analysis_direction, "direct_direction": row.analysis_direction})
    pd.DataFrame(pairs).to_csv(out / "proxy_semantics.csv", index=False, lineterminator="\n")
    annual_path = ROOT / "outputs/long_history_multi_evaluator_screening_v1/primary_full_20260907/primary/evidence_v0/data_quality_by_year.csv"
    receipt = json.loads((REPORT / "EVIDENCE_V0_RECEIPT.json").read_text(encoding="utf-8"))
    assert digest(annual_path) == receipt["file_hashes"][annual_path.name]
    annual = pd.read_csv(annual_path)
    annual.loc[annual.factor.isin(board.loc[board.low_sample_coverage, "factor"])].to_csv(out / "low_coverage_by_year.csv", index=False, lineterminator="\n")
    counts = review.review_recommendation.value_counts().to_dict()
    summary = {"status": "assistant_review_complete_user_decision_pending", "primary_modified": False,
               "held_aside_recent_diagnostic_accessed": False, "new_factor_evaluation_run": False,
               "counts": counts, "factors": len(review), "blocked": int((~inventory.research_usable).sum()),
               "same_expression_groups": len(overlaps), "proxy_semantics_pairs_usable": len(pairs),
               "source_board_sha256": digest(REPORT / "candidate_board.csv"), "source_manifest_sha256": digest(REPORT / "PRIMARY_V0_MANIFEST.json"),
               "source_annual_quality_sha256": digest(annual_path),
               "rule_id": manifest["rule_id"],
               "review_method": "Existing agreement/flags route every factor; definitions and named case notes provide qualitative review. No new pass thresholds, ranking or final pool.",
               "opposite_annual_periods_definition": "all available annual means opposite to frozen direction; not restricted to >=126-day qualified years; descriptive only"}
    (out / "review_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    assert sum(counts.values()) == 765 and len(overlaps) == 8
    assert review.user_decision.eq("pending").all()
    for name in ("candidate_board.csv", "factor_evidence_board.csv", "factor_inventory.csv"):
        assert digest(REPORT / name) == manifest["file_hashes"][f"reports/long_history_multi_evaluator_screening_v1/{name}"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
