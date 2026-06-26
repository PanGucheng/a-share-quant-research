from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from factor_research.report import markdown_table


RANK_IC_COLUMNS = [
    "alphalens_rank_ic_10d",
    "alphalens_rank_ic_20d",
    "jqfactor_rank_ic_10d",
    "jqfactor_rank_ic_20d",
    "qlib_rank_ic_10d",
    "qlib_rank_ic_20d",
]
RANK_ICIR_COLUMNS = [
    "alphalens_rank_icir_10d",
    "alphalens_rank_icir_20d",
    "jqfactor_rank_icir_10d",
    "jqfactor_rank_icir_20d",
    "qlib_rank_icir_10d",
    "qlib_rank_icir_20d",
]
WIN_RATE_COLUMNS = [
    "alphalens_rank_ic_win_rate_10d",
    "alphalens_rank_ic_win_rate_20d",
    "jqfactor_rank_ic_win_rate_10d",
    "jqfactor_rank_ic_win_rate_20d",
    "qlib_rank_ic_win_rate_10d",
    "qlib_rank_ic_win_rate_20d",
]
MONOTONICITY_COLUMNS = [
    "alphalens_monotonicity_10d",
    "alphalens_monotonicity_20d",
    "jqfactor_monotonicity_10d",
    "jqfactor_monotonicity_20d",
]
TURNOVER_COLUMNS = [
    "alphalens_turnover_mean_top_1d",
    "alphalens_turnover_mean_top_5d",
    "jqfactor_turnover_mean_top_1",
    "jqfactor_turnover_mean_top_5",
]


@dataclass(frozen=True)
class JudgementRules:
    min_coverage: float = 0.99
    max_missing_rate: float = 0.01
    weak_abs_rank_ic: float = 0.015
    consistent_abs_rank_ic: float = 0.03
    strong_abs_rank_ic: float = 0.05
    consistent_abs_rank_icir: float = 0.20
    strong_abs_rank_icir: float = 0.35
    consistent_win_rate: float = 0.53
    strong_win_rate: float = 0.58
    min_direction_agreement_ratio: float = 0.67
    strong_direction_agreement_ratio: float = 0.83
    high_turnover_top1: float = 0.65
    high_turnover_top5: float = 0.80
    min_abs_monotonicity: float = 0.50
    context_flip_tolerance: float = 0.005
    redundancy_corr_threshold: float = 0.90


@dataclass(frozen=True)
class Alpha158JudgementConfig:
    screening_input: Path
    context_group_ic: Path
    correlation_summary: Path
    correlation_pairs: Path
    output_dir: Path
    rules: JudgementRules


def read_csv_or_empty(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def numeric(row: pd.Series, column: str) -> float:
    if column not in row:
        return np.nan
    value = pd.to_numeric(pd.Series([row[column]]), errors="coerce").iloc[0]
    return float(value) if pd.notna(value) else np.nan


def numeric_values(row: pd.Series, columns: list[str]) -> list[float]:
    values = []
    for column in columns:
        value = numeric(row, column)
        if pd.notna(value):
            values.append(value)
    return values


def sign(value: float, tolerance: float = 1e-12) -> int:
    if pd.isna(value) or abs(value) <= tolerance:
        return 0
    return 1 if value > 0 else -1


def sign_text(value: int) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"


def direction_metrics(row: pd.Series) -> dict:
    rank_values = numeric_values(row, RANK_IC_COLUMNS)
    if not rank_values:
        return {
            "primary_rank_ic": np.nan,
            "primary_abs_rank_ic": np.nan,
            "consensus_direction": "neutral",
            "direction_agreement_count": 0,
            "direction_observation_count": 0,
            "direction_agreement_ratio": np.nan,
        }
    primary_candidates = [
        numeric(row, "alphalens_rank_ic_20d"),
        numeric(row, "qlib_rank_ic_20d"),
        numeric(row, "jqfactor_rank_ic_20d"),
        numeric(row, "alphalens_rank_ic_10d"),
        numeric(row, "qlib_rank_ic_10d"),
        numeric(row, "jqfactor_rank_ic_10d"),
    ]
    primary_rank_ic = next((value for value in primary_candidates if pd.notna(value)), np.nan)
    direction_seed = np.nanmedian(rank_values)
    consensus_sign = sign(direction_seed)
    if consensus_sign == 0:
        strongest = rank_values[int(np.nanargmax(np.abs(rank_values)))]
        consensus_sign = sign(strongest)
    signs = [sign(value) for value in rank_values if sign(value) != 0]
    agreement_count = sum(1 for item in signs if item == consensus_sign)
    observation_count = len(signs)
    agreement_ratio = agreement_count / observation_count if observation_count else np.nan
    return {
        "primary_rank_ic": primary_rank_ic,
        "primary_abs_rank_ic": abs(primary_rank_ic) if pd.notna(primary_rank_ic) else np.nan,
        "max_abs_rank_ic": float(np.nanmax(np.abs(rank_values))),
        "consensus_direction": sign_text(consensus_sign),
        "consensus_direction_sign": consensus_sign,
        "direction_agreement_count": agreement_count,
        "direction_observation_count": observation_count,
        "direction_agreement_ratio": agreement_ratio,
    }


def max_abs_metric(row: pd.Series, columns: list[str]) -> float:
    values = numeric_values(row, columns)
    if not values:
        return np.nan
    return float(np.nanmax(np.abs(values)))


def max_metric(row: pd.Series, columns: list[str]) -> float:
    values = numeric_values(row, columns)
    if not values:
        return np.nan
    return float(np.nanmax(values))


def turnover_metrics(row: pd.Series, rules: JudgementRules) -> dict:
    top1 = max_metric(row, ["alphalens_turnover_mean_top_1d", "jqfactor_turnover_mean_top_1"])
    top5 = max_metric(row, ["alphalens_turnover_mean_top_5d", "jqfactor_turnover_mean_top_5"])
    high = (
        (pd.notna(top1) and top1 >= rules.high_turnover_top1)
        or (pd.notna(top5) and top5 >= rules.high_turnover_top5)
    )
    return {"turnover_top1_max": top1, "turnover_top5_max": top5, "high_turnover": high}


def monotonicity_metrics(row: pd.Series, rules: JudgementRules) -> dict:
    values = numeric_values(row, MONOTONICITY_COLUMNS)
    if not values:
        return {"max_abs_monotonicity": np.nan, "low_monotonicity": True}
    max_abs = float(np.nanmax(np.abs(values)))
    return {"max_abs_monotonicity": max_abs, "low_monotonicity": max_abs < rules.min_abs_monotonicity}


def build_context_stability(context_group_ic: pd.DataFrame) -> pd.DataFrame:
    if context_group_ic.empty:
        return pd.DataFrame(columns=["factor"])
    rows = []
    source = context_group_ic[
        (context_group_ic["system"].eq("alphalens_reloaded"))
        & (context_group_ic["return_mode"].eq("raw_return"))
        & (context_group_ic["group_dimension"].eq("index_segment"))
    ].copy()
    for factor, group in source.groupby("factor"):
        row: dict[str, object] = {"factor": factor}
        for horizon in ["10D", "20D"]:
            sub = group[group["horizon"].astype(str).str.upper().eq(horizon.upper())]
            if sub.empty:
                continue
            item = sub.iloc[0]
            suffix = horizon.lower()
            row[f"context_mean_rank_ic_{suffix}"] = numeric(item, "mean_group_rank_ic")
            row[f"context_min_rank_ic_{suffix}"] = numeric(item, "min_group_rank_ic")
            row[f"context_max_rank_ic_{suffix}"] = numeric(item, "max_group_rank_ic")
            row[f"context_min_group_{suffix}"] = item.get("min_group", "")
            row[f"context_max_group_{suffix}"] = item.get("max_group", "")
        rows.append(row)
    return pd.DataFrame(rows)


def context_flags(row: pd.Series, rules: JudgementRules) -> dict:
    direction = int(row.get("consensus_direction_sign", 0))
    if direction == 0:
        return {"unstable_context": True, "context_reason": "neutral_direction"}
    reasons = []
    for horizon in ["10d", "20d"]:
        mean_value = numeric(row, f"context_mean_rank_ic_{horizon}")
        min_value = numeric(row, f"context_min_rank_ic_{horizon}")
        max_value = numeric(row, f"context_max_rank_ic_{horizon}")
        if pd.isna(mean_value):
            continue
        if sign(mean_value, rules.context_flip_tolerance) not in {0, direction}:
            reasons.append(f"{horizon}_mean_flips")
        if direction > 0 and pd.notna(min_value) and min_value < -rules.context_flip_tolerance:
            reasons.append(f"{horizon}_min_group_flips")
        if direction < 0 and pd.notna(max_value) and max_value > rules.context_flip_tolerance:
            reasons.append(f"{horizon}_max_group_flips")
    return {"unstable_context": bool(reasons), "context_reason": ",".join(reasons)}


def signal_label(row: pd.Series, rules: JudgementRules) -> tuple[str, str]:
    if str(row.get("evaluation_gate", "")) == "holdout" or bool(row.get("holdout", False)):
        return "holdout", "evaluation_holdout"
    if str(row.get("evaluation_gate", "")) != "strict_screening_input":
        return "review", "not_strict_screening_input"
    if numeric(row, "coverage") < rules.min_coverage:
        return "data_quality_issue", "low_coverage"
    if numeric(row, "missing_rate") > rules.max_missing_rate:
        return "data_quality_issue", "high_missing_rate"
    if int(row.get("context_failed_count", 0)) > 0:
        return "data_quality_issue", "context_failed"
    max_abs_ic = numeric(row, "max_abs_rank_ic")
    max_abs_icir = numeric(row, "max_abs_rank_icir")
    max_win_rate = numeric(row, "max_rank_ic_win_rate")
    agreement = numeric(row, "direction_agreement_ratio")
    if pd.isna(max_abs_ic) or max_abs_ic < rules.weak_abs_rank_ic:
        return "weak_signal", "rank_ic_below_weak_threshold"
    strong = (
        max_abs_ic >= rules.strong_abs_rank_ic
        and max_abs_icir >= rules.strong_abs_rank_icir
        and max_win_rate >= rules.strong_win_rate
        and agreement >= rules.strong_direction_agreement_ratio
    )
    if strong:
        return "strong_signal", "passes_strong_rank_ic_icir_winrate_agreement"
    consistent = (
        max_abs_ic >= rules.consistent_abs_rank_ic
        and max_abs_icir >= rules.consistent_abs_rank_icir
        and max_win_rate >= rules.consistent_win_rate
        and agreement >= rules.min_direction_agreement_ratio
    )
    if consistent:
        return "consistent_signal", "passes_consistent_rank_ic_icir_winrate_agreement"
    return "review", "mixed_or_marginal_signal"


class UnionFind:
    def __init__(self, items: list[str]) -> None:
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        parent = self.parent.setdefault(item, item)
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left

    def groups(self) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for item in sorted(self.parent):
            result.setdefault(self.find(item), []).append(item)
        return result


def build_redundancy_clusters(
    board: pd.DataFrame,
    correlation_summary: pd.DataFrame,
    correlation_pairs: pd.DataFrame,
    rules: JudgementRules,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    strict_factors = sorted(board[board["evaluation_gate"].eq("strict_screening_input")]["factor"].tolist())
    uf = UnionFind(strict_factors)
    edge_rows = []
    if not correlation_pairs.empty:
        for row in correlation_pairs.itertuples(index=False):
            left = str(row.factor_a)
            right = str(row.factor_b)
            corr = float(row.abs_mean_daily_spearman_corr)
            if left in uf.parent and right in uf.parent and corr >= rules.redundancy_corr_threshold:
                uf.union(left, right)
                edge_rows.append(
                    {
                        "factor_a": left,
                        "factor_b": right,
                        "abs_corr": corr,
                        "source": "top_pairs",
                    }
                )
    if not correlation_summary.empty:
        for row in correlation_summary.itertuples(index=False):
            left = str(row.factor)
            right = str(row.strongest_corr_factor)
            corr = float(row.strongest_abs_corr) if pd.notna(row.strongest_abs_corr) else np.nan
            if left in uf.parent and right in uf.parent and pd.notna(corr) and corr >= rules.redundancy_corr_threshold:
                uf.union(left, right)
                edge_rows.append(
                    {
                        "factor_a": left,
                        "factor_b": right,
                        "abs_corr": corr,
                        "source": "strongest_corr",
                    }
                )

    rank_frame = representative_rank_frame(board)
    cluster_rows = []
    factor_rows = []
    cluster_id = 1
    for _, members in sorted(uf.groups().items(), key=lambda item: (min(item[1]), len(item[1]))):
        if len(members) < 2:
            continue
        member_rank = rank_frame[rank_frame["factor"].isin(members)].sort_values(
            [
                "selection_signal_rank",
                "selection_issue_rank",
                "direction_agreement_ratio",
                "primary_abs_rank_ic",
                "max_abs_rank_icir",
                "turnover_top1_max",
                "coverage",
                "factor",
            ],
            ascending=[True, True, False, False, False, True, False, True],
        )
        representative = str(member_rank.iloc[0]["factor"])
        cluster_name = f"C{cluster_id:03d}"
        cluster_rows.append(
            {
                "cluster_id": cluster_name,
                "representative_factor": representative,
                "factor_count": len(members),
                "factors": ",".join(sorted(members)),
                "selection_policy": "ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage",
            }
        )
        for member in sorted(members):
            factor_rows.append(
                {
                    "cluster_id": cluster_name,
                    "factor": member,
                    "cluster_representative": representative,
                    "is_cluster_representative": member == representative,
                }
            )
        cluster_id += 1
    return pd.DataFrame(cluster_rows), pd.DataFrame(factor_rows)


def representative_rank_frame(board: pd.DataFrame) -> pd.DataFrame:
    signal_order = {
        "strong_signal": 0,
        "consistent_signal": 1,
        "review": 2,
        "weak_signal": 3,
        "data_quality_issue": 8,
        "holdout": 9,
    }
    rows = []
    for row in board.itertuples(index=False):
        item = row._asdict()
        issue_rank = 0
        if item.get("high_turnover"):
            issue_rank += 2
        if item.get("unstable_context"):
            issue_rank += 2
        if item.get("low_monotonicity"):
            issue_rank += 1
        rows.append(
            {
                "factor": item["factor"],
                "selection_signal_rank": signal_order.get(item.get("signal_label"), 5),
                "selection_issue_rank": issue_rank,
                "direction_agreement_ratio": item.get("direction_agreement_ratio", np.nan),
                "primary_abs_rank_ic": item.get("primary_abs_rank_ic", np.nan),
                "max_abs_rank_icir": item.get("max_abs_rank_icir", np.nan),
                "turnover_top1_max": item.get("turnover_top1_max", np.nan),
                "coverage": item.get("coverage", np.nan),
            }
        )
    return pd.DataFrame(rows)


def final_label(row: pd.Series) -> str:
    if row.get("signal_label") == "holdout":
        return "holdout"
    if row.get("signal_label") == "data_quality_issue":
        return "data_quality_issue"
    if bool(row.get("is_redundant", False)):
        return "redundant"
    if bool(row.get("high_turnover", False)):
        return "high_turnover"
    if bool(row.get("unstable_context", False)):
        return "unstable_context"
    return str(row.get("signal_label", "review"))


def issue_tags(row: pd.Series) -> str:
    tags = []
    for column, label in [
        ("high_turnover", "high_turnover"),
        ("unstable_context", "unstable_context"),
        ("low_monotonicity", "low_monotonicity"),
        ("is_redundant", "redundant"),
    ]:
        if bool(row.get(column, False)):
            tags.append(label)
    return ",".join(tags)


def build_judgement_board(config: Alpha158JudgementConfig) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source = read_csv_or_empty(config.screening_input)
    if source.empty:
        raise FileNotFoundError(f"Missing or empty screening input: {config.screening_input}")
    context = build_context_stability(read_csv_or_empty(config.context_group_ic))
    correlation_summary = read_csv_or_empty(config.correlation_summary)
    correlation_pairs = read_csv_or_empty(config.correlation_pairs)

    board = source.copy()
    direction_rows = [direction_metrics(row) for _, row in board.iterrows()]
    board = pd.concat([board.reset_index(drop=True), pd.DataFrame(direction_rows)], axis=1)
    board["max_abs_rank_icir"] = board.apply(lambda row: max_abs_metric(row, RANK_ICIR_COLUMNS), axis=1)
    board["max_rank_ic_win_rate"] = board.apply(lambda row: max_metric(row, WIN_RATE_COLUMNS), axis=1)
    board = pd.concat([board, pd.DataFrame([turnover_metrics(row, config.rules) for _, row in board.iterrows()])], axis=1)
    board = pd.concat([board, pd.DataFrame([monotonicity_metrics(row, config.rules) for _, row in board.iterrows()])], axis=1)
    if not context.empty:
        board = board.merge(context, on="factor", how="left")
    context_flag_rows = [context_flags(row, config.rules) for _, row in board.iterrows()]
    board = pd.concat([board.reset_index(drop=True), pd.DataFrame(context_flag_rows)], axis=1)
    labels = [signal_label(row, config.rules) for _, row in board.iterrows()]
    board["signal_label"] = [item[0] for item in labels]
    board["signal_reason"] = [item[1] for item in labels]

    cluster_summary, cluster_membership = build_redundancy_clusters(
        board, correlation_summary, correlation_pairs, config.rules
    )
    if not cluster_membership.empty:
        board = board.merge(cluster_membership, on="factor", how="left")
    else:
        board["cluster_id"] = ""
        board["cluster_representative"] = ""
        board["is_cluster_representative"] = False
    board["cluster_id"] = board["cluster_id"].fillna("")
    board["cluster_representative"] = board["cluster_representative"].fillna("")
    board["is_cluster_representative"] = board["is_cluster_representative"].where(
        board["is_cluster_representative"].notna(), False
    ).astype(bool)
    board["is_redundant"] = board["cluster_id"].ne("") & ~board["is_cluster_representative"]
    board["judgement_label"] = board.apply(final_label, axis=1)
    board["issue_tags"] = board.apply(issue_tags, axis=1)
    board["judgement_policy"] = "ordered_rules_no_combined_score"

    output_columns = [
        "factor",
        "category",
        "evaluation_gate",
        "judgement_label",
        "signal_label",
        "signal_reason",
        "issue_tags",
        "consensus_direction",
        "direction_agreement_count",
        "direction_observation_count",
        "direction_agreement_ratio",
        "primary_rank_ic",
        "primary_abs_rank_ic",
        "max_abs_rank_ic",
        "max_abs_rank_icir",
        "max_rank_ic_win_rate",
        "coverage",
        "missing_rate",
        "alphalens_status",
        "jqfactor_status",
        "qlib_status",
        "context_failed_count",
        "unstable_context",
        "context_reason",
        "high_turnover",
        "turnover_top1_max",
        "turnover_top5_max",
        "low_monotonicity",
        "max_abs_monotonicity",
        "strongest_corr_factor",
        "strongest_abs_corr",
        "cluster_id",
        "cluster_representative",
        "is_cluster_representative",
        "is_redundant",
        "holdout_reason",
        "failure_steps",
        "judgement_policy",
    ]
    for column in output_columns:
        if column not in board.columns:
            board[column] = np.nan
    board = board[output_columns].sort_values(
        ["judgement_label", "cluster_id", "primary_abs_rank_ic", "factor"],
        ascending=[True, True, False, True],
    )
    return board.reset_index(drop=True), cluster_summary, cluster_membership


def write_report(output_dir: Path, board: pd.DataFrame, clusters: pd.DataFrame, rules: JudgementRules) -> None:
    judgement_counts = board.groupby("judgement_label").size().reset_index(name="count")
    signal_counts = board.groupby("signal_label").size().reset_index(name="count")
    issue_counts = issue_count_frame(board)
    representative_view = (
        board[board["is_cluster_representative"].eq(True)][
            [
                "cluster_id",
                "factor",
                "judgement_label",
                "consensus_direction",
                "primary_rank_ic",
                "max_abs_rank_icir",
                "turnover_top1_max",
                "coverage",
            ]
        ].head(40)
        if not board.empty
        else pd.DataFrame()
    )
    strong_view = board[board["judgement_label"].isin(["strong_signal", "consistent_signal"])][
        [
            "factor",
            "judgement_label",
            "consensus_direction",
            "primary_rank_ic",
            "max_abs_rank_icir",
            "max_rank_ic_win_rate",
            "issue_tags",
            "cluster_id",
        ]
    ].head(40)
    holdouts = board[board["judgement_label"].eq("holdout")][["factor", "holdout_reason", "failure_steps"]]
    lines = [
        "# Alpha158 Judgement Layer V1",
        "",
        "This layer assigns explainable rule labels on top of the existing Alpha158 screening input.",
        "It keeps source evaluator metrics intact and does not create a combined score.",
        "",
        "## Rule Snapshot",
        "",
        markdown_table(pd.DataFrame([rules.__dict__])),
        "",
        "## Judgement Counts",
        "",
        markdown_table(judgement_counts),
        "",
        "## Signal Counts Before Issue Priority",
        "",
        markdown_table(signal_counts),
        "",
        "## Issue Counts",
        "",
        markdown_table(issue_counts),
        "",
        "## Redundancy Clusters",
        "",
        markdown_table(clusters.head(40) if not clusters.empty else clusters),
        "",
        "## Cluster Representatives",
        "",
        markdown_table(representative_view),
        "",
        "## Signal Candidates",
        "",
        markdown_table(strong_view),
        "",
        "## Holdouts",
        "",
        markdown_table(holdouts),
        "",
        "## Output Files",
        "",
        "- `alpha158_judgement_board.csv`",
        "- `alpha158_redundancy_clusters.csv`",
        "- `alpha158_redundancy_cluster_members.csv`",
        "- `alpha158_judgement_report.md`",
        "",
        "## Notes",
        "",
        "- `redundant` means the factor is highly correlated with a selected cluster representative under the configured threshold.",
        "- Representatives are selected by ordered criteria, not by a hidden aggregate score.",
        "- `high_turnover` and `unstable_context` are issue-priority labels; the raw signal label is preserved in `signal_label`.",
        "- This output is a research triage board, not a trading signal.",
    ]
    (output_dir / "alpha158_judgement_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def issue_count_frame(board: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column, label in [
        ("high_turnover", "high_turnover"),
        ("unstable_context", "unstable_context"),
        ("low_monotonicity", "low_monotonicity"),
        ("is_redundant", "redundant"),
    ]:
        rows.append({"issue": label, "count": int(board[column].fillna(False).astype(bool).sum())})
    return pd.DataFrame(rows)


def run_alpha158_judgement(config: Alpha158JudgementConfig) -> dict[str, pd.DataFrame]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    board, clusters, cluster_members = build_judgement_board(config)
    board.to_csv(config.output_dir / "alpha158_judgement_board.csv", index=False, encoding="utf-8-sig")
    clusters.to_csv(config.output_dir / "alpha158_redundancy_clusters.csv", index=False, encoding="utf-8-sig")
    cluster_members.to_csv(
        config.output_dir / "alpha158_redundancy_cluster_members.csv", index=False, encoding="utf-8-sig"
    )
    write_report(config.output_dir, board, clusters, config.rules)
    return {"board": board, "clusters": clusters, "cluster_members": cluster_members}
