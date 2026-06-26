from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

import pandas as pd

from factor_research.report import markdown_table


ALPHA_LABELS = {"strong_signal", "consistent_signal"}
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Alpha158CandidatePoolMetadata:
    pool_name: str
    source_judgement_board: str
    source_redundancy_clusters: str
    description: str = "Alpha158 candidate pool generated from judgement layer V1."


@dataclass(frozen=True)
class Alpha158CandidatePoolConfig:
    judgement_board: Path
    redundancy_clusters: Path
    redundancy_cluster_members: Path
    output_dir: Path
    pool_name: str


def read_csv_or_empty(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def load_judgement_board(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing judgement board: {path}")
    board = pd.read_csv(path)
    required = [
        "factor",
        "judgement_label",
        "signal_label",
        "evaluation_gate",
        "is_redundant",
        "high_turnover",
        "unstable_context",
    ]
    missing = [column for column in required if column not in board.columns]
    if missing:
        raise ValueError(f"judgement board missing required columns: {missing}")
    return board


def as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


def candidate_role(row: pd.Series) -> tuple[str, bool, str]:
    judgement = str(row.get("judgement_label", ""))
    if judgement == "holdout":
        return "holdout", False, "evaluation_holdout"
    if judgement == "redundant" or as_bool(row.get("is_redundant", False)):
        return "excluded_redundant", False, "non_representative_redundant_factor"
    if judgement == "high_turnover" or as_bool(row.get("high_turnover", False)):
        return "excluded_high_turnover", False, "high_turnover_issue"
    if judgement == "unstable_context" or as_bool(row.get("unstable_context", False)):
        return "excluded_unstable_context", False, "context_instability_issue"
    if (
        judgement in ALPHA_LABELS
        and str(row.get("evaluation_gate")) == "strict_screening_input"
        and not as_bool(row.get("is_redundant", False))
    ):
        return "alpha_candidate", True, f"{judgement}_accepted"
    if judgement == "weak_signal":
        return "monitor", False, "weak_signal_monitor"
    return "monitor", False, "review_or_marginal_signal"


def build_candidate_pool(
    judgement_board: pd.DataFrame,
    metadata: Alpha158CandidatePoolMetadata,
) -> pd.DataFrame:
    rows = []
    for _, source in judgement_board.iterrows():
        role, included, reason = candidate_role(source)
        rows.append(
            {
                "pool_name": metadata.pool_name,
                "factor": source["factor"],
                "role": role,
                "included": included,
                "pool_reason": reason,
                "judgement_label": source.get("judgement_label"),
                "signal_label": source.get("signal_label"),
                "signal_reason": source.get("signal_reason"),
                "category": source.get("category"),
                "consensus_direction": source.get("consensus_direction"),
                "primary_rank_ic": source.get("primary_rank_ic"),
                "primary_abs_rank_ic": source.get("primary_abs_rank_ic"),
                "max_abs_rank_ic": source.get("max_abs_rank_ic"),
                "max_abs_rank_icir": source.get("max_abs_rank_icir"),
                "max_rank_ic_win_rate": source.get("max_rank_ic_win_rate"),
                "coverage": source.get("coverage"),
                "missing_rate": source.get("missing_rate"),
                "issue_tags": source.get("issue_tags"),
                "high_turnover": source.get("high_turnover"),
                "unstable_context": source.get("unstable_context"),
                "context_reason": source.get("context_reason"),
                "low_monotonicity": source.get("low_monotonicity"),
                "cluster_id": source.get("cluster_id"),
                "cluster_representative": source.get("cluster_representative"),
                "is_cluster_representative": source.get("is_cluster_representative"),
                "is_redundant": source.get("is_redundant"),
                "turnover_top1_max": source.get("turnover_top1_max"),
                "turnover_top5_max": source.get("turnover_top5_max"),
                "strongest_corr_factor": source.get("strongest_corr_factor"),
                "strongest_abs_corr": source.get("strongest_abs_corr"),
                "source_judgement_board": metadata.source_judgement_board,
            }
        )
    pool = pd.DataFrame(rows)
    role_order = {
        "alpha_candidate": 0,
        "monitor": 1,
        "excluded_high_turnover": 2,
        "excluded_unstable_context": 3,
        "excluded_redundant": 4,
        "holdout": 5,
    }
    pool["_role_order"] = pool["role"].map(role_order).fillna(99)
    pool["primary_abs_rank_ic"] = pd.to_numeric(pool["primary_abs_rank_ic"], errors="coerce")
    pool["max_abs_rank_icir"] = pd.to_numeric(pool["max_abs_rank_icir"], errors="coerce")
    pool = pool.sort_values(
        ["_role_order", "primary_abs_rank_ic", "max_abs_rank_icir", "factor"],
        ascending=[True, False, False, True],
    )
    return pool.drop(columns=["_role_order"]).reset_index(drop=True)


def pool_to_json(pool: pd.DataFrame, metadata: Alpha158CandidatePoolMetadata) -> dict:
    clean = pool.where(pd.notna(pool), None)
    groups = {
        role: frame.where(pd.notna(frame), None).to_dict(orient="records")
        for role, frame in clean.groupby("role", sort=False)
    }
    return {
        "metadata": asdict(metadata),
        "role_counts": clean.groupby("role").size().to_dict() if not clean.empty else {},
        "alpha_candidates": clean[clean["role"].eq("alpha_candidate")].to_dict(orient="records"),
        "groups": groups,
        "records": clean.to_dict(orient="records"),
    }


def write_outputs(
    pool: pd.DataFrame,
    clusters: pd.DataFrame,
    members: pd.DataFrame,
    metadata: Alpha158CandidatePoolMetadata,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    alpha = pool[pool["role"].eq("alpha_candidate")].copy()
    pool.to_csv(output_dir / "alpha158_candidate_pool.csv", index=False, encoding="utf-8-sig")
    alpha.to_csv(output_dir / "alpha158_alpha_candidates.csv", index=False, encoding="utf-8-sig")
    payload = pool_to_json(pool, metadata)
    (output_dir / "alpha158_candidate_pool.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_report(pool, alpha, clusters, members, metadata, output_dir / "alpha158_candidate_pool_report.md")


def write_report(
    pool: pd.DataFrame,
    alpha: pd.DataFrame,
    clusters: pd.DataFrame,
    members: pd.DataFrame,
    metadata: Alpha158CandidatePoolMetadata,
    output: Path,
) -> None:
    role_counts = pool.groupby("role").size().reset_index(name="count") if not pool.empty else pd.DataFrame()
    signal_counts = (
        alpha.groupby(["judgement_label", "consensus_direction"]).size().reset_index(name="count")
        if not alpha.empty
        else pd.DataFrame()
    )
    alpha_view_cols = [
        "factor",
        "judgement_label",
        "consensus_direction",
        "primary_rank_ic",
        "max_abs_rank_icir",
        "max_rank_ic_win_rate",
        "cluster_id",
        "issue_tags",
    ]
    excluded_summary = (
        pool[~pool["role"].eq("alpha_candidate")]
        .groupby(["role", "pool_reason"])
        .size()
        .reset_index(name="count")
        if not pool.empty
        else pd.DataFrame()
    )
    cluster_alpha = alpha[alpha["cluster_id"].notna() & alpha["cluster_id"].astype(str).ne("")][
        ["factor", "cluster_id", "cluster_representative", "is_cluster_representative"]
    ] if not alpha.empty else pd.DataFrame()
    lines = [
        "# Alpha158 Candidate Pool V1",
        "",
        f"- Pool name: `{metadata.pool_name}`",
        f"- Source judgement board: `{metadata.source_judgement_board}`",
        f"- Source redundancy clusters: `{metadata.source_redundancy_clusters}`",
        "",
        "## Role Counts",
        "",
        table(role_counts),
        "",
        "## Alpha Candidate Signal Counts",
        "",
        table(signal_counts),
        "",
        "## Alpha Candidates",
        "",
        table(alpha[alpha_view_cols] if not alpha.empty else pd.DataFrame()),
        "",
        "## Alpha Candidates From Clusters",
        "",
        table(cluster_alpha),
        "",
        "## Excluded Or Monitor Summary",
        "",
        table(excluded_summary),
        "",
        "## Redundancy Cluster Snapshot",
        "",
        table(clusters.head(30) if not clusters.empty else clusters),
        "",
        "## Cluster Member Count",
        "",
        f"- Cluster rows: `{len(clusters)}`",
        f"- Cluster member rows: `{len(members)}`",
        "",
        "## Output Files",
        "",
        "- `alpha158_candidate_pool.csv`",
        "- `alpha158_alpha_candidates.csv`",
        "- `alpha158_candidate_pool.json`",
        "- `alpha158_candidate_pool_report.md`",
        "",
        "## Notes",
        "",
        "- The candidate pool is a research interface, not a trading signal.",
        "- `alpha_candidate` is intentionally conservative in V1.",
        "- Low monotonicity is preserved as a warning in `issue_tags` and does not remove a factor in V1.",
        "- Non-representative redundant factors are excluded from alpha candidates.",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return markdown_table(frame)
    return markdown_table(frame.where(pd.notna(frame), ""))


def run_alpha158_candidate_pool(config: Alpha158CandidatePoolConfig) -> dict[str, pd.DataFrame]:
    board = load_judgement_board(config.judgement_board)
    clusters = read_csv_or_empty(config.redundancy_clusters)
    members = read_csv_or_empty(config.redundancy_cluster_members)
    metadata = Alpha158CandidatePoolMetadata(
        pool_name=config.pool_name,
        source_judgement_board=display_path(config.judgement_board),
        source_redundancy_clusters=display_path(config.redundancy_clusters),
    )
    pool = build_candidate_pool(board, metadata)
    write_outputs(pool, clusters, members, metadata, config.output_dir)
    return {"pool": pool, "clusters": clusters, "members": members}
