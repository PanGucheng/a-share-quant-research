from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from factor_research.registry import FactorSpec, spec_map
from factor_research.report import markdown_table


MAIN_WINDOW = "main_research_2021_2023"
OOS_WINDOW = "recent_oos_2024_2026"
RAW_NEUTRALIZATION = "raw"
JOINT_NEUTRALIZATION = "liquidity_volatility_residual"


@dataclass(frozen=True)
class ScreeningRules:
    min_coverage: float = 0.90
    max_missing_rate: float = 0.10
    research_min_rank_ic: float = 0.015
    portfolio_min_rank_ic: float = 0.030
    min_oos_rank_ic: float = 0.005
    min_rank_icir: float = 0.10
    min_ic_win_rate: float = 0.52
    min_slice_stability: float = 0.55
    min_directional_spread: float = 0.0
    min_residual_retention: float = 0.25
    exposure_corr_threshold: float = 0.80
    redundancy_corr_threshold: float = 0.85


def read_csv_or_empty(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def load_screening_inputs(input_dir: Path) -> dict[str, pd.DataFrame]:
    return {
        "summary": read_csv_or_empty(input_dir / "factor_neutralized_summary.csv"),
        "group_summary": read_csv_or_empty(input_dir / "factor_neutralized_group_return_summary.csv"),
        "slice_ic": read_csv_or_empty(input_dir / "factor_slice_ic.csv"),
        "slice_group_summary": read_csv_or_empty(input_dir / "factor_slice_group_return_summary.csv"),
        "exposure_corr": read_csv_or_empty(input_dir / "factor_exposure_correlation.csv"),
        "factor_corr": read_csv_or_empty(input_dir / "factor_neutralized_correlation.csv"),
        "changelog": read_csv_or_empty(input_dir / "factor_candidate_changelog.csv"),
    }


def numeric(value) -> float:
    result = pd.to_numeric(value, errors="coerce")
    return float(result) if pd.notna(result) else np.nan


def first_row(frame: pd.DataFrame) -> pd.Series | None:
    return None if frame.empty else frame.iloc[0]


def metric(row: pd.Series | None, column: str) -> float:
    if row is None or column not in row:
        return np.nan
    return numeric(row[column])


def raw_factor(base_factor: str) -> str:
    return f"{base_factor}__raw"


def group_directional_spread(group_summary: pd.DataFrame, factor: str, label: str, spec: FactorSpec) -> float:
    if group_summary.empty:
        return np.nan
    rows = group_summary[
        (group_summary["window"] == MAIN_WINDOW)
        & (group_summary["label"] == label)
        & (group_summary["factor"] == raw_factor(factor))
    ].copy()
    if rows.empty:
        return np.nan
    rows["quantile"] = pd.to_numeric(rows["quantile"], errors="coerce")
    rows["mean_group_return"] = pd.to_numeric(rows["mean_group_return"], errors="coerce")
    rows = rows.dropna(subset=["quantile", "mean_group_return"]).sort_values("quantile")
    if len(rows) < 2:
        return np.nan
    spread = rows.iloc[-1]["mean_group_return"] - rows.iloc[0]["mean_group_return"]
    return spread * spec.direction_sign if spec.direction_sign is not None else np.nan


def slice_stability(slice_ic: pd.DataFrame, factor: str, label: str) -> tuple[int, int, float, float]:
    if slice_ic.empty:
        return 0, 0, np.nan, np.nan
    rows = slice_ic[
        (slice_ic["window"] == MAIN_WINDOW)
        & (slice_ic["label"] == label)
        & (slice_ic["factor"] == raw_factor(factor))
    ].copy()
    if rows.empty or "directional_mean_rank_ic" not in rows.columns:
        return 0, 0, np.nan, np.nan
    values = pd.to_numeric(rows["directional_mean_rank_ic"], errors="coerce").dropna()
    if values.empty:
        return 0, int(len(rows)), np.nan, np.nan
    positive = int((values > 0).sum())
    count = int(len(values))
    return positive, count, positive / count if count else np.nan, float(values.min())


def strongest_exposure(exposure_corr: pd.DataFrame, factor: str) -> tuple[str, float]:
    if exposure_corr.empty:
        return "", np.nan
    rows = exposure_corr[(exposure_corr["window"] == MAIN_WINDOW) & (exposure_corr["factor"] == factor)].copy()
    if rows.empty:
        return "", np.nan
    rows["abs_mean_spearman_corr"] = pd.to_numeric(rows["abs_mean_spearman_corr"], errors="coerce")
    row = rows.sort_values("abs_mean_spearman_corr", ascending=False).iloc[0]
    return str(row["exposure"]), numeric(row["abs_mean_spearman_corr"])


def neutralization_metrics(changelog: pd.DataFrame, factor: str, label: str) -> tuple[float, float, float]:
    if changelog.empty:
        return np.nan, np.nan, np.nan
    rows = changelog[
        (changelog["window"] == MAIN_WINDOW)
        & (changelog["label"] == label)
        & (changelog["base_factor"] == factor)
    ]
    raw = first_row(rows[rows["neutralization"] == RAW_NEUTRALIZATION])
    joint = first_row(rows[rows["neutralization"] == JOINT_NEUTRALIZATION])
    raw_ic = metric(raw, "directional_mean_rank_ic")
    joint_ic = metric(joint, "directional_mean_rank_ic")
    delta = metric(joint, "delta_directional_rank_ic")
    retention = joint_ic / raw_ic if pd.notna(raw_ic) and raw_ic != 0 and pd.notna(joint_ic) else np.nan
    return joint_ic, delta, retention


def strongest_raw_correlation(factor_corr: pd.DataFrame, factor: str, known_factors: set[str], label: str) -> tuple[str, float]:
    if factor_corr.empty:
        return "", np.nan
    target = raw_factor(factor)
    raw_names = {raw_factor(name): name for name in known_factors}
    rows = factor_corr[
        (factor_corr["window"] == MAIN_WINDOW)
        & (factor_corr["label"] == label)
        & ((factor_corr["factor_a"] == target) | (factor_corr["factor_b"] == target))
    ].copy()
    if rows.empty:
        return "", np.nan
    rows["other"] = np.where(rows["factor_a"] == target, rows["factor_b"], rows["factor_a"])
    rows = rows[rows["other"].isin(raw_names.keys()) & (rows["other"] != target)]
    if rows.empty:
        return "", np.nan
    rows["abs_corr"] = pd.to_numeric(rows["spearman_corr"], errors="coerce").abs()
    row = rows.sort_values("abs_corr", ascending=False).iloc[0]
    return raw_names.get(str(row["other"]), str(row["other"])), numeric(row["abs_corr"])


def decide_status(row: dict, spec: FactorSpec, rules: ScreeningRules) -> tuple[str, str]:
    reasons: list[str] = []
    if spec.direction_sign is None:
        return "watch", "direction_not_defined"
    if pd.isna(row["main_directional_rank_ic"]):
        return "reject", "missing_main_ic"
    if row["coverage"] < rules.min_coverage:
        reasons.append("low_coverage")
    if row["missing_rate"] > rules.max_missing_rate:
        reasons.append("high_missing_rate")
    if pd.notna(row["oos_directional_rank_ic"]) and row["oos_directional_rank_ic"] < 0:
        reasons.append("negative_oos")
    if row["main_directional_rank_ic"] < 0:
        reasons.append("negative_main_ic")
    if reasons:
        return "reject", "|".join(reasons)

    exposure_dominated = (
        pd.notna(row["dominant_exposure_corr"])
        and row["dominant_exposure_corr"] >= rules.exposure_corr_threshold
        and (
            pd.isna(row["residual_retention"])
            or row["residual_retention"] < rules.min_residual_retention
            or row["joint_residual_directional_rank_ic"] <= 0.01
        )
    )
    if exposure_dominated:
        return "risk_exposure", "strong_raw_signal_but_exposure_dominated"

    portfolio_ready = (
        row["main_directional_rank_ic"] >= rules.portfolio_min_rank_ic
        and row["directional_rank_icir"] >= rules.min_rank_icir
        and row["ic_win_rate"] >= rules.min_ic_win_rate
        and row["oos_directional_rank_ic"] >= rules.min_oos_rank_ic
        and row["slice_stability"] >= rules.min_slice_stability
        and row["directional_group_spread"] > rules.min_directional_spread
        and row["residual_retention"] >= rules.min_residual_retention
    )
    if portfolio_ready:
        return "portfolio_test_candidate", "passes_screening_rules"

    research_ready = (
        row["main_directional_rank_ic"] >= rules.research_min_rank_ic
        and (pd.isna(row["oos_directional_rank_ic"]) or row["oos_directional_rank_ic"] >= 0)
        and (pd.isna(row["directional_group_spread"]) or row["directional_group_spread"] > rules.min_directional_spread)
    )
    if research_ready:
        return "research_candidate", "partial_signal_needs_more_validation"
    return "watch", "insufficient_evidence"


def build_candidate_board(inputs: dict[str, pd.DataFrame], specs: list[FactorSpec], rules: ScreeningRules | None = None) -> pd.DataFrame:
    rules = rules or ScreeningRules()
    summary = inputs["summary"]
    if summary.empty:
        return pd.DataFrame()
    spec_by_name = spec_map(specs)
    labels = sorted(summary["label"].dropna().unique().tolist())
    known_factors = set(spec_by_name.keys())
    rows = []
    for label in labels:
        for factor, spec in spec_by_name.items():
            main = first_row(
                summary[
                    (summary["window"] == MAIN_WINDOW)
                    & (summary["label"] == label)
                    & (summary["factor"] == raw_factor(factor))
                ]
            )
            oos = first_row(
                summary[
                    (summary["window"] == OOS_WINDOW)
                    & (summary["label"] == label)
                    & (summary["factor"] == raw_factor(factor))
                ]
            )
            if main is None:
                continue
            positive_slices, slice_count, stability, worst_slice = slice_stability(inputs["slice_ic"], factor, label)
            joint_ic, joint_delta, retention = neutralization_metrics(inputs["changelog"], factor, label)
            exposure, exposure_corr = strongest_exposure(inputs["exposure_corr"], factor)
            corr_factor, corr_value = strongest_raw_correlation(inputs["factor_corr"], factor, known_factors, label)
            row = {
                "label": label,
                "factor": factor,
                "category": spec.category,
                "expected_direction": spec.expected_direction,
                "coverage": metric(main, "coverage"),
                "missing_rate": metric(main, "missing_rate"),
                "main_directional_rank_ic": metric(main, "directional_mean_rank_ic"),
                "directional_rank_icir": metric(main, "directional_rank_icir"),
                "ic_win_rate": metric(main, "ic_win_rate"),
                "oos_directional_rank_ic": metric(oos, "directional_mean_rank_ic"),
                "directional_group_spread": group_directional_spread(inputs["group_summary"], factor, label, spec),
                "positive_slices": positive_slices,
                "slice_count": slice_count,
                "slice_stability": stability,
                "worst_slice_directional_rank_ic": worst_slice,
                "joint_residual_directional_rank_ic": joint_ic,
                "joint_residual_delta": joint_delta,
                "residual_retention": retention,
                "dominant_exposure": exposure,
                "dominant_exposure_corr": exposure_corr,
                "most_correlated_factor": corr_factor,
                "most_correlated_factor_corr": corr_value,
            }
            status, reason = decide_status(row, spec, rules)
            row["status"] = status
            row["reason"] = reason
            rows.append(row)
    board = pd.DataFrame(rows)
    if board.empty:
        return board
    board = apply_redundancy(board, rules)
    status_order = {
        "portfolio_test_candidate": 0,
        "research_candidate": 1,
        "risk_exposure": 2,
        "redundant": 3,
        "watch": 4,
        "reject": 5,
    }
    board["_status_order"] = board["status"].map(status_order).fillna(99)
    return board.sort_values(["label", "_status_order", "main_directional_rank_ic"], ascending=[True, True, False]).drop(
        columns=["_status_order"]
    )


def apply_redundancy(board: pd.DataFrame, rules: ScreeningRules) -> pd.DataFrame:
    result = board.copy()
    candidates = result[result["status"].isin(["portfolio_test_candidate", "research_candidate"])].copy()
    for label, group in candidates.groupby("label"):
        accepted: list[str] = []
        group = group.sort_values("main_directional_rank_ic", ascending=False)
        for row in group.itertuples(index=False):
            correlated = []
            for accepted_factor in accepted:
                mask = (result["label"] == label) & (result["factor"] == row.factor)
                other_corr = result.loc[mask, "most_correlated_factor_corr"].iloc[0]
                other_name = result.loc[mask, "most_correlated_factor"].iloc[0]
                if other_name == accepted_factor and pd.notna(other_corr) and other_corr >= rules.redundancy_corr_threshold:
                    correlated.append(accepted_factor)
            if correlated:
                mask = (result["label"] == label) & (result["factor"] == row.factor)
                result.loc[mask, "status"] = "redundant"
                result.loc[mask, "reason"] = "highly_correlated_with_stronger_candidate:" + ",".join(correlated)
            else:
                accepted.append(row.factor)
    return result


def write_screening_report(board: pd.DataFrame, output: Path, input_dir: Path, rules: ScreeningRules) -> None:
    status_counts = board.groupby("status").size().reset_index(name="count") if not board.empty else pd.DataFrame()
    top_view = (
        board[
            [
                "factor",
                "status",
                "reason",
                "main_directional_rank_ic",
                "directional_rank_icir",
                "oos_directional_rank_ic",
                "slice_stability",
                "residual_retention",
                "dominant_exposure",
                "dominant_exposure_corr",
            ]
        ].head(30)
        if not board.empty
        else pd.DataFrame()
    )
    exposure_view = (
        board[board["status"] == "risk_exposure"][
            [
                "factor",
                "reason",
                "main_directional_rank_ic",
                "joint_residual_directional_rank_ic",
                "residual_retention",
                "dominant_exposure",
                "dominant_exposure_corr",
            ]
        ]
        if not board.empty and (board["status"] == "risk_exposure").any()
        else pd.DataFrame()
    )
    lines = [
        "# Factor Screening V3.3 Report",
        "",
        f"- Input directory: `{input_dir}`",
        f"- Min portfolio directional Rank IC: `{rules.portfolio_min_rank_ic}`",
        f"- Min OOS directional Rank IC: `{rules.min_oos_rank_ic}`",
        f"- Min residual retention: `{rules.min_residual_retention}`",
        f"- Exposure correlation threshold: `{rules.exposure_corr_threshold}`",
        "",
        "## Status Counts",
        "",
        markdown_table(status_counts),
        "",
        "## Candidate Board",
        "",
        markdown_table(top_view),
        "",
        "## Risk Exposure Diagnostics",
        "",
        markdown_table(exposure_view),
        "",
        "## Output Files",
        "",
        "- `factor_candidate_board.csv`",
        "- `factor_screening_report.md`",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
