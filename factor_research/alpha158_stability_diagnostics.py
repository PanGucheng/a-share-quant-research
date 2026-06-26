from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from factor_research.report import markdown_table


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Alpha158StabilityDiagnosticsConfig:
    main_dir: Path
    recent_dir: Path
    output_dir: Path


def read_csv_required(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required diagnostics input: {path}")
    return pd.read_csv(path)


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def rank_desc(frame: pd.DataFrame, metric: str, rank_col: str) -> pd.DataFrame:
    ranked = frame.copy()
    ranked[rank_col] = ranked[metric].rank(ascending=False, method="min")
    return ranked


def stability_label(row: pd.Series) -> str:
    main_ir = row["main_net_excess_ir"]
    recent_ir = row["recent_net_excess_ir"]
    if recent_ir >= 0.5 and main_ir >= 0.3:
        return "stable_positive"
    if recent_ir >= 0.5 and recent_ir > main_ir:
        return "oos_improved"
    if main_ir >= 0.5 and recent_ir < 0.2:
        return "main_only"
    if main_ir > 0 and recent_ir > 0:
        return "positive_but_weaker_oos"
    if recent_ir <= 0:
        return "weak_or_negative_oos"
    return "review"


def compare_single_factors(main_dir: Path, recent_dir: Path) -> pd.DataFrame:
    main = read_csv_required(main_dir / "single_factor_summary.csv")
    recent = read_csv_required(recent_dir / "single_factor_summary.csv")
    main = rank_desc(main, "net_excess_ir", "main_rank")
    recent = rank_desc(recent, "net_excess_ir", "recent_rank")
    cols = ["factor", "issue_tags", "net_excess_ir", "net_annualized_excess", "average_turnover", "net_max_drawdown"]
    merged = main[cols + ["main_rank"]].merge(
        recent[cols + ["recent_rank"]],
        on="factor",
        how="inner",
        suffixes=("_main", "_recent"),
    )
    merged = merged.rename(
        columns={
            "issue_tags_main": "issue_tags",
            "net_excess_ir_main": "main_net_excess_ir",
            "net_excess_ir_recent": "recent_net_excess_ir",
            "net_annualized_excess_main": "main_net_annualized_excess",
            "net_annualized_excess_recent": "recent_net_annualized_excess",
            "average_turnover_main": "main_average_turnover",
            "average_turnover_recent": "recent_average_turnover",
            "net_max_drawdown_main": "main_net_max_drawdown",
            "net_max_drawdown_recent": "recent_net_max_drawdown",
        }
    )
    merged["rank_change"] = merged["recent_rank"] - merged["main_rank"]
    merged["net_excess_ir_delta"] = merged["recent_net_excess_ir"] - merged["main_net_excess_ir"]
    merged["turnover_delta"] = merged["recent_average_turnover"] - merged["main_average_turnover"]
    merged["stability_label"] = merged.apply(stability_label, axis=1)
    return merged.sort_values(["stability_label", "recent_net_excess_ir"], ascending=[True, False])


def compare_by_key(main: pd.DataFrame, recent: pd.DataFrame, key: str) -> pd.DataFrame:
    metric_cols = ["net_excess_ir", "net_annualized_excess", "average_turnover", "net_max_drawdown"]
    merged = main[[key, *metric_cols]].merge(
        recent[[key, *metric_cols]],
        on=key,
        how="inner",
        suffixes=("_main", "_recent"),
    )
    for metric in metric_cols:
        merged[f"{metric}_delta"] = merged[f"{metric}_recent"] - merged[f"{metric}_main"]
    return merged


def compare_topk(main_dir: Path, recent_dir: Path) -> pd.DataFrame:
    return compare_by_key(
        read_csv_required(main_dir / "topk_sensitivity.csv"),
        read_csv_required(recent_dir / "topk_sensitivity.csv"),
        "topk",
    ).sort_values("topk")


def compare_cost(main_dir: Path, recent_dir: Path) -> pd.DataFrame:
    return compare_by_key(
        read_csv_required(main_dir / "cost_sensitivity.csv"),
        read_csv_required(recent_dir / "cost_sensitivity.csv"),
        "cost_bps",
    ).sort_values("cost_bps")


def compare_liquidity_exposure(main_dir: Path, recent_dir: Path) -> pd.DataFrame:
    main = read_csv_required(main_dir / "liquidity_bucket_exposure.csv")
    recent = read_csv_required(recent_dir / "liquidity_bucket_exposure.csv")
    merged = main[["liquidity_bucket", "position_share"]].merge(
        recent[["liquidity_bucket", "position_share"]],
        on="liquidity_bucket",
        how="outer",
        suffixes=("_main", "_recent"),
    ).fillna(0.0)
    merged["position_share_delta"] = merged["position_share_recent"] - merged["position_share_main"]
    return merged.sort_values("liquidity_bucket")


def write_report(
    config: Alpha158StabilityDiagnosticsConfig,
    single: pd.DataFrame,
    topk: pd.DataFrame,
    cost: pd.DataFrame,
    exposure: pd.DataFrame,
) -> None:
    label_counts = single.groupby("stability_label").size().reset_index(name="count")
    top_single = single.sort_values("recent_net_excess_ir", ascending=False).head(10)
    lines = [
        "# Alpha158 Stability Diagnostics V1",
        "",
        f"- Main diagnostics: `{display_path(config.main_dir)}`",
        f"- Recent diagnostics: `{display_path(config.recent_dir)}`",
        "",
        "## Stability Label Counts",
        "",
        markdown_table(label_counts),
        "",
        "## Single Factor Stability",
        "",
        markdown_table(top_single.fillna("")),
        "",
        "## TopK Delta",
        "",
        markdown_table(topk),
        "",
        "## Cost Delta",
        "",
        markdown_table(cost),
        "",
        "## Liquidity Bucket Exposure Delta",
        "",
        markdown_table(exposure),
        "",
        "## Notes",
        "",
        "- Recent OOS is materially weaker than the 2021-2023 main window for the combined candidate portfolio.",
        "- Candidate ranking is not stable enough to move directly into strategy optimization.",
        "- The next stage should diagnose risk exposures and consider lower-turnover score construction.",
    ]
    (config.output_dir / "alpha158_stability_diagnostics_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def run_alpha158_stability_diagnostics(config: Alpha158StabilityDiagnosticsConfig) -> dict[str, pd.DataFrame]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    single = compare_single_factors(config.main_dir, config.recent_dir)
    topk = compare_topk(config.main_dir, config.recent_dir)
    cost = compare_cost(config.main_dir, config.recent_dir)
    exposure = compare_liquidity_exposure(config.main_dir, config.recent_dir)
    single.to_csv(config.output_dir / "single_factor_stability.csv", index=False, encoding="utf-8-sig")
    topk.to_csv(config.output_dir / "topk_sensitivity_delta.csv", index=False, encoding="utf-8-sig")
    cost.to_csv(config.output_dir / "cost_sensitivity_delta.csv", index=False, encoding="utf-8-sig")
    exposure.to_csv(config.output_dir / "liquidity_bucket_exposure_delta.csv", index=False, encoding="utf-8-sig")
    write_report(config, single, topk, cost, exposure)
    return {
        "single_factor_stability": single,
        "topk_sensitivity_delta": topk,
        "cost_sensitivity_delta": cost,
        "liquidity_bucket_exposure_delta": exposure,
    }
