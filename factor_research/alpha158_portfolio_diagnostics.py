from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from factor_research.alpha158_portfolio_smoke import (
    Alpha158PortfolioSmokeConfig,
    build_portfolio_frame,
    candidate_weight_table,
    display_path,
    load_alpha_candidates,
    load_candidate_factor_frame,
    load_label_frame,
    score_candidates,
)
from factor_research.report import markdown_table
from scripts.run_low_frequency_tradability_portfolio import run_low_frequency_portfolio


@dataclass(frozen=True)
class Alpha158PortfolioDiagnosticsConfig:
    base: Alpha158PortfolioSmokeConfig
    output_dir: Path
    topk_values: list[int]
    cost_bps_values: list[float]


def scenario_summary(name: str, scenario_type: str, summary: dict, extra: dict | None = None) -> dict:
    row = {"scenario": name, "scenario_type": scenario_type}
    if extra:
        row.update(extra)
    row.update(summary)
    return row


def run_scenario(
    portfolio_frame: pd.DataFrame,
    config: Alpha158PortfolioSmokeConfig,
    topk: int | None = None,
    cost_bps: float | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    return run_low_frequency_portfolio(
        portfolio_frame,
        config.label,
        int(topk if topk is not None else config.topk),
        config.rebalance_every,
        float(cost_bps if cost_bps is not None else config.cost_bps),
        config.min_liquidity_bucket,
        config.min_tradability_score,
        config.min_capacity_multiple,
    )


def liquidity_bucket_exposure(positions: pd.DataFrame) -> pd.DataFrame:
    if positions.empty:
        return pd.DataFrame()
    exposure = (
        positions.groupby("liquidity_bucket")
        .size()
        .reset_index(name="position_count")
        .sort_values("liquidity_bucket")
    )
    total = exposure["position_count"].sum()
    exposure["position_share"] = exposure["position_count"] / total if total else 0.0
    return exposure


def compact_columns(frame: pd.DataFrame) -> pd.DataFrame:
    preferred = [
        "scenario",
        "scenario_type",
        "factor",
        "topk",
        "cost_bps",
        "candidate_count",
        "trading_days",
        "executed_rebalances",
        "net_annualized_excess",
        "net_excess_ir",
        "average_turnover",
        "net_max_drawdown",
        "average_eligible_count",
        "average_selected_count",
    ]
    return frame[[column for column in preferred if column in frame.columns]]


def write_report(
    config: Alpha158PortfolioDiagnosticsConfig,
    base_summary: pd.DataFrame,
    single_factor: pd.DataFrame,
    topk: pd.DataFrame,
    cost: pd.DataFrame,
    exposure: pd.DataFrame,
    output: Path,
) -> None:
    top_single = (
        single_factor.sort_values("net_excess_ir", ascending=False).head(14)
        if "net_excess_ir" in single_factor.columns
        else single_factor
    )
    lines = [
        "# Alpha158 Portfolio Diagnostics V1",
        "",
        f"- Base smoke output: `{display_path(config.base.output_dir)}`",
        f"- Candidate pool: `{display_path(config.base.candidate_pool)}`",
        f"- Date range: `{config.base.start_time}` to `{config.base.end_time}`",
        f"- Base TopK: `{config.base.topk}`",
        f"- Base cost bps: `{config.base.cost_bps}`",
        "",
        "## Base Summary",
        "",
        markdown_table(compact_columns(base_summary)),
        "",
        "## Single Factor Summary",
        "",
        markdown_table(compact_columns(top_single)),
        "",
        "## TopK Sensitivity",
        "",
        markdown_table(compact_columns(topk)),
        "",
        "## Cost Sensitivity",
        "",
        markdown_table(compact_columns(cost)),
        "",
        "## Liquidity Bucket Exposure",
        "",
        markdown_table(exposure),
        "",
        "## Notes",
        "",
        "- This diagnostic layer does not change candidate selection or optimize parameters.",
        "- High turnover remains the main portfolio-level risk to address before strategy work.",
        "- Recent OOS diagnostics require extending the Alpha158 expression frame beyond 2024-02-29.",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(
    config: Alpha158PortfolioDiagnosticsConfig,
    base_summary: pd.DataFrame,
    single_factor: pd.DataFrame,
    topk: pd.DataFrame,
    cost: pd.DataFrame,
    exposure: pd.DataFrame,
) -> None:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    base_summary.to_csv(config.output_dir / "base_summary.csv", index=False, encoding="utf-8-sig")
    single_factor.to_csv(config.output_dir / "single_factor_summary.csv", index=False, encoding="utf-8-sig")
    topk.to_csv(config.output_dir / "topk_sensitivity.csv", index=False, encoding="utf-8-sig")
    cost.to_csv(config.output_dir / "cost_sensitivity.csv", index=False, encoding="utf-8-sig")
    exposure.to_csv(config.output_dir / "liquidity_bucket_exposure.csv", index=False, encoding="utf-8-sig")
    write_report(
        config,
        base_summary,
        single_factor,
        topk,
        cost,
        exposure,
        config.output_dir / "alpha158_portfolio_diagnostics_report.md",
    )


def run_alpha158_portfolio_diagnostics(config: Alpha158PortfolioDiagnosticsConfig) -> dict[str, pd.DataFrame]:
    candidates = load_alpha_candidates(config.base.candidate_pool)
    weights = candidate_weight_table(candidates, config.base.score_policy)
    factor_frame = load_candidate_factor_frame(config.base.expression_frame_dir, weights["factor"].tolist())
    label_frame = load_label_frame(config.base)

    combined_score, _ = score_candidates(
        factor_frame,
        weights,
        config.base.start_time,
        config.base.end_time,
        config.base.score_clip,
        config.base.min_score_components,
    )
    combined_frame = build_portfolio_frame(combined_score, label_frame, config.base.tradability_dir)
    _, _, base_positions, base = run_scenario(combined_frame, config.base)
    base["candidate_count"] = int(len(weights))
    base_summary = pd.DataFrame([scenario_summary("combined_base", "base", base)])

    single_rows = []
    for row in weights.itertuples(index=False):
        one_weight = pd.DataFrame([row._asdict()])
        score_frame, _ = score_candidates(
            factor_frame[["datetime", "instrument", row.factor]].copy(),
            one_weight,
            config.base.start_time,
            config.base.end_time,
            config.base.score_clip,
            1,
        )
        portfolio_frame = build_portfolio_frame(score_frame, label_frame, config.base.tradability_dir)
        _, _, _, summary = run_scenario(portfolio_frame, config.base)
        summary["candidate_count"] = 1
        single_rows.append(
            scenario_summary(
                row.factor,
                "single_factor",
                summary,
                {"factor": row.factor, "issue_tags": row.issue_tags},
            )
        )
    single_factor = pd.DataFrame(single_rows)

    topk_rows = []
    for topk in config.topk_values:
        _, _, _, summary = run_scenario(combined_frame, config.base, topk=topk)
        summary["candidate_count"] = int(len(weights))
        topk_rows.append(scenario_summary(f"topk_{topk}", "topk_sensitivity", summary, {"topk": topk}))
    topk_frame = pd.DataFrame(topk_rows)

    cost_rows = []
    for cost_bps in config.cost_bps_values:
        _, _, _, summary = run_scenario(combined_frame, config.base, cost_bps=cost_bps)
        summary["candidate_count"] = int(len(weights))
        cost_rows.append(
            scenario_summary(f"cost_{cost_bps:g}bps", "cost_sensitivity", summary, {"cost_bps": cost_bps})
        )
    cost_frame = pd.DataFrame(cost_rows)
    exposure = liquidity_bucket_exposure(base_positions)
    write_outputs(config, base_summary, single_factor, topk_frame, cost_frame, exposure)
    return {
        "base_summary": base_summary,
        "single_factor": single_factor,
        "topk_sensitivity": topk_frame,
        "cost_sensitivity": cost_frame,
        "liquidity_bucket_exposure": exposure,
    }
