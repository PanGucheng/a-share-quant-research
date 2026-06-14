from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

import pandas as pd

from factor_research.report import markdown_table


ROLE_BY_STATUS = {
    "portfolio_test_candidate": "alpha_candidate",
    "research_candidate": "alpha_candidate",
    "risk_exposure": "risk_control",
    "watch": "monitor",
    "redundant": "excluded",
    "reject": "excluded",
}


@dataclass(frozen=True)
class CandidatePoolMetadata:
    pool_name: str
    source_board: str
    label: str
    description: str = "Factor candidate pool generated from factor screening V3 outputs."


def load_candidate_board(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing candidate board: {path}")
    board = pd.read_csv(path)
    required = ["label", "factor", "status", "reason"]
    missing = [column for column in required if column not in board.columns]
    if missing:
        raise ValueError(f"candidate board missing required columns: {missing}")
    return board


def build_candidate_pool(board: pd.DataFrame, metadata: CandidatePoolMetadata) -> pd.DataFrame:
    result = board.copy()
    result = result[result["label"] == metadata.label].copy()
    if result.empty:
        return pd.DataFrame()
    result["role"] = result["status"].map(ROLE_BY_STATUS).fillna("monitor")
    result["pool_name"] = metadata.pool_name
    result["source_board"] = metadata.source_board
    ordered_columns = [
        "pool_name",
        "label",
        "factor",
        "role",
        "status",
        "reason",
        "category",
        "expected_direction",
        "main_directional_rank_ic",
        "directional_rank_icir",
        "oos_directional_rank_ic",
        "slice_stability",
        "residual_retention",
        "dominant_exposure",
        "dominant_exposure_corr",
        "most_correlated_factor",
        "most_correlated_factor_corr",
        "source_board",
    ]
    for column in ordered_columns:
        if column not in result.columns:
            result[column] = pd.NA
    role_order = {"alpha_candidate": 0, "risk_control": 1, "monitor": 2, "excluded": 3}
    result["_role_order"] = result["role"].map(role_order).fillna(99)
    result["main_directional_rank_ic"] = pd.to_numeric(result["main_directional_rank_ic"], errors="coerce")
    result = result.sort_values(["_role_order", "main_directional_rank_ic"], ascending=[True, False])
    return result[ordered_columns]


def pool_to_json(pool: pd.DataFrame, metadata: CandidatePoolMetadata) -> dict:
    records = pool.where(pd.notna(pool), None).to_dict(orient="records")
    groups: dict[str, list[dict]] = {}
    for role, role_frame in pool.groupby("role", sort=False):
        groups[role] = role_frame.where(pd.notna(role_frame), None).to_dict(orient="records")
    return {
        "metadata": asdict(metadata),
        "role_counts": pool.groupby("role").size().to_dict() if not pool.empty else {},
        "groups": groups,
        "records": records,
    }


def write_pool_outputs(pool: pd.DataFrame, metadata: CandidatePoolMetadata, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pool.to_csv(output_dir / "factor_candidate_pool.csv", index=False, encoding="utf-8-sig")
    payload = pool_to_json(pool, metadata)
    (output_dir / "factor_candidate_pool.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_pool_report(pool, metadata, output_dir / "factor_candidate_pool_report.md")


def write_pool_report(pool: pd.DataFrame, metadata: CandidatePoolMetadata, output: Path) -> None:
    role_counts = pool.groupby("role").size().reset_index(name="count") if not pool.empty else pd.DataFrame()
    alpha = pool[pool["role"] == "alpha_candidate"] if not pool.empty else pd.DataFrame()
    risk = pool[pool["role"] == "risk_control"] if not pool.empty else pd.DataFrame()
    monitor = pool[pool["role"] == "monitor"] if not pool.empty else pd.DataFrame()
    columns = [
        "factor",
        "role",
        "status",
        "reason",
        "main_directional_rank_ic",
        "oos_directional_rank_ic",
        "residual_retention",
        "dominant_exposure",
        "dominant_exposure_corr",
    ]
    lines = [
        "# Factor Candidate Pool V3.4 Report",
        "",
        f"- Pool name: `{metadata.pool_name}`",
        f"- Label: `{metadata.label}`",
        f"- Source board: `{metadata.source_board}`",
        "",
        "## Role Counts",
        "",
        markdown_table(role_counts),
        "",
        "## Alpha Candidates",
        "",
        markdown_table(alpha[columns] if not alpha.empty else pd.DataFrame()),
        "",
        "## Risk Controls",
        "",
        markdown_table(risk[columns] if not risk.empty else pd.DataFrame()),
        "",
        "## Monitor List",
        "",
        markdown_table(monitor[columns] if not monitor.empty else pd.DataFrame()),
        "",
        "## Output Files",
        "",
        "- `factor_candidate_pool.csv`",
        "- `factor_candidate_pool.json`",
        "- `factor_candidate_pool_report.md`",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
