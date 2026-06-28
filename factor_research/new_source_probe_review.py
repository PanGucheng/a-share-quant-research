from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from factor_research.report import markdown_table


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ProbeReviewRules:
    high_abs_corr: float
    high_abs_tradability_exposure: float
    min_probe_rows: int
    min_redundancy_pairs: int
    min_oos_candidates: int


@dataclass(frozen=True)
class ProbeReviewConfig:
    diagnostic_board: Path
    correlation_pairs: Path
    tradability_exposure: Path
    output_dir: Path
    rules: ProbeReviewRules


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, item: str) -> str:
        self.parent.setdefault(item, item)
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left

    def groups(self) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for item in list(self.parent):
            root = self.find(item)
            result.setdefault(root, []).append(item)
        return {root: sorted(items) for root, items in result.items() if len(items) > 1}


def portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_csv_required(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(f"Missing or empty required input: {path}")
    return pd.read_csv(path)


def numeric(value: object) -> float:
    result = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(result) if pd.notna(result) else np.nan


def probe_quality_score(row: pd.Series, high_exposure: bool) -> float:
    label = str(row.get("judgement_label", ""))
    label_score = {"strong_signal_probe": 100.0, "consistent_signal_probe": 60.0}.get(label, 0.0)
    portfolio_bonus = 20.0 if str(row.get("portfolio_smoke_selected", "")).lower() in {"true", "1"} else 0.0
    frame_bonus = 5.0 if str(row.get("frame_diagnostic_selected", "")).lower() in {"true", "1"} else 0.0
    ic_score = 100.0 * (numeric(row.get("max_abs_mean_ic")) if pd.notna(numeric(row.get("max_abs_mean_ic"))) else 0.0)
    ir_score = 5.0 * (numeric(row.get("max_abs_qlib_ir")) if pd.notna(numeric(row.get("max_abs_qlib_ir"))) else 0.0)
    agreement = 10.0 * (
        numeric(row.get("direction_agreement_ratio")) if pd.notna(numeric(row.get("direction_agreement_ratio"))) else 0.0
    )
    exposure_penalty = 50.0 if high_exposure else 0.0
    return label_score + portfolio_bonus + frame_bonus + ic_score + ir_score + agreement - exposure_penalty


def redundancy_pairs(correlation_pairs: pd.DataFrame, threshold: float) -> pd.DataFrame:
    if correlation_pairs.empty:
        return pd.DataFrame(columns=["factor_a", "factor_b", "mean_daily_spearman_corr", "abs_mean_daily_spearman_corr", "date_count"])
    pairs = correlation_pairs.copy()
    pairs["abs_mean_daily_spearman_corr"] = pd.to_numeric(pairs["abs_mean_daily_spearman_corr"], errors="coerce")
    return pairs[pairs["abs_mean_daily_spearman_corr"].ge(threshold)].sort_values(
        "abs_mean_daily_spearman_corr", ascending=False
    )


def build_redundancy_groups(
    board: pd.DataFrame,
    pairs: pd.DataFrame,
    exposure_watch: set[str],
) -> tuple[pd.DataFrame, dict[str, str], set[str]]:
    uf = UnionFind()
    for row in pairs.itertuples(index=False):
        uf.union(str(row.factor_a), str(row.factor_b))
    groups = uf.groups()
    if not groups:
        return pd.DataFrame(), {}, set()
    board_by_factor = board.drop_duplicates("factor").set_index("factor")
    representative_map: dict[str, str] = {}
    redundant_factors: set[str] = set()
    rows: list[dict[str, Any]] = []
    for group_id, factors in enumerate(groups.values(), start=1):
        scored = []
        for factor in factors:
            if factor not in board_by_factor.index:
                continue
            row = board_by_factor.loc[factor]
            high_exposure = factor in exposure_watch
            scored.append((probe_quality_score(row, high_exposure), factor))
        if not scored:
            continue
        representative = sorted(scored, reverse=True)[0][1]
        for factor in factors:
            representative_map[factor] = representative
            if factor != representative:
                redundant_factors.add(factor)
        source_families = sorted(set(str(board_by_factor.loc[factor].get("source_family", "")) for factor in factors if factor in board_by_factor.index))
        rows.append(
            {
                "group_id": f"redundancy_group_{group_id:03d}",
                "representative_factor": representative,
                "group_size": len(factors),
                "source_families": ",".join(source_families),
                "factor_list": ",".join(factors),
            }
        )
    return pd.DataFrame(rows), representative_map, redundant_factors


def review_action(
    row: pd.Series,
    representative_map: dict[str, str],
    redundant_factors: set[str],
    exposure_watch: set[str],
) -> str:
    factor = str(row["factor"])
    if factor in exposure_watch:
        return "tradability_exposure_review"
    if factor in redundant_factors:
        return "redundant_holdout_candidate"
    if representative_map.get(factor) == factor:
        return "redundancy_representative_review"
    if str(row.get("portfolio_smoke_selected", "")).lower() in {"true", "1"}:
        return "oos_extension_candidate"
    if str(row.get("frame_diagnostic_selected", "")).lower() in {"true", "1"}:
        return "frame_review_candidate"
    return "metric_only_defer"


def build_review_board(
    board: pd.DataFrame,
    exposure: pd.DataFrame,
    representative_map: dict[str, str],
    redundant_factors: set[str],
    rules: ProbeReviewRules,
) -> pd.DataFrame:
    result = board.copy()
    exposure_cols = ["factor", "max_abs_tradability_exposure", "mean_spearman_liquidity_value", "mean_spearman_liquidity_bucket"]
    exposure_cols = [column for column in exposure_cols if column in exposure.columns]
    if exposure_cols:
        result = result.merge(exposure[exposure_cols], on="factor", how="left", suffixes=("", "_review"))
    result["max_abs_tradability_exposure"] = pd.to_numeric(
        result.get("max_abs_tradability_exposure", pd.Series(np.nan, index=result.index)),
        errors="coerce",
    )
    exposure_watch = set(result.loc[result["max_abs_tradability_exposure"].ge(rules.high_abs_tradability_exposure), "factor"])
    result["redundancy_representative"] = result["factor"].map(representative_map).fillna("")
    result["review_action"] = result.apply(
        lambda row: review_action(row, representative_map, redundant_factors, exposure_watch),
        axis=1,
    )
    action_order = {
        "oos_extension_candidate": 0,
        "redundancy_representative_review": 1,
        "frame_review_candidate": 2,
        "tradability_exposure_review": 3,
        "redundant_holdout_candidate": 4,
        "metric_only_defer": 5,
    }
    result["_action_order"] = result["review_action"].map(action_order).fillna(9)
    return result.sort_values(["_action_order", "source_family", "factor"]).drop(columns=["_action_order"]).reset_index(drop=True)


def build_contract_status(
    board: pd.DataFrame,
    pairs: pd.DataFrame,
    groups: pd.DataFrame,
    exposure_watch: pd.DataFrame,
    oos_candidates: pd.DataFrame,
    rules: ProbeReviewRules,
) -> pd.DataFrame:
    rows = [
        {
            "check_id": "review_board_rows",
            "status": "pass" if len(board) >= rules.min_probe_rows else "blocked",
            "detail": f"rows={len(board)}",
        },
        {
            "check_id": "redundancy_pairs_present",
            "status": "pass" if len(pairs) >= rules.min_redundancy_pairs else "partial",
            "detail": f"pairs={len(pairs)}",
        },
        {
            "check_id": "redundancy_groups_present",
            "status": "pass" if len(groups) > 0 else "partial",
            "detail": f"groups={len(groups)}",
        },
        {
            "check_id": "tradability_exposure_watchlist_present",
            "status": "pass" if len(exposure_watch) > 0 else "partial",
            "detail": f"watchlist={len(exposure_watch)}",
        },
        {
            "check_id": "oos_candidates_present",
            "status": "pass" if len(oos_candidates) >= rules.min_oos_candidates else "partial",
            "detail": f"candidates={len(oos_candidates)}",
        },
        {
            "check_id": "no_downstream_default",
            "status": "pass"
            if not board.get("downstream_default_included", pd.Series(False, index=board.index)).astype(bool).any()
            else "blocked",
            "detail": f"downstream_default={int(board.get('downstream_default_included', pd.Series(False, index=board.index)).astype(bool).sum())}",
        },
    ]
    return pd.DataFrame(rows)


def write_report(
    config: ProbeReviewConfig,
    board: pd.DataFrame,
    pairs: pd.DataFrame,
    groups: pd.DataFrame,
    exposure_watch: pd.DataFrame,
    oos_candidates: pd.DataFrame,
    contract: pd.DataFrame,
) -> None:
    action_counts = board.groupby(["source_family", "review_action"]).size().reset_index(name="count")
    lines = [
        "# New-Source Probe Review V1",
        "",
        f"- Diagnostic board: `{portable_path(config.diagnostic_board)}`",
        "- Scope: review triage only; no model training, no strategy optimization, no evaluator definition changes.",
        "",
        "## Contract Status",
        "",
        markdown_table(contract),
        "",
        "## Review Action Counts",
        "",
        markdown_table(action_counts),
        "",
        "## Redundancy Groups",
        "",
        markdown_table(groups.head(30)),
        "",
        "## Tradability Exposure Watchlist",
        "",
        markdown_table(exposure_watch.head(30)),
        "",
        "## OOS Extension Candidates",
        "",
        markdown_table(oos_candidates.head(30)),
        "",
        "## Notes",
        "",
        "- `oos_extension_candidate` is still a research queue label, not a model input.",
        "- Redundant and tradability-exposed probes should be reviewed before any training stage.",
    ]
    (config.output_dir / "probe_review_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_probe_review(config: ProbeReviewConfig) -> dict[str, pd.DataFrame]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    board = read_csv_required(config.diagnostic_board)
    corr_pairs = read_csv_required(config.correlation_pairs)
    exposure = read_csv_required(config.tradability_exposure)
    pairs = redundancy_pairs(corr_pairs, config.rules.high_abs_corr)
    exposure["max_abs_tradability_exposure"] = pd.to_numeric(exposure["max_abs_tradability_exposure"], errors="coerce")
    exposure_watch = exposure[exposure["max_abs_tradability_exposure"].ge(config.rules.high_abs_tradability_exposure)].sort_values(
        "max_abs_tradability_exposure", ascending=False
    )
    exposure_watch_set = set(exposure_watch["factor"].astype(str))
    groups, representative_map, redundant_factors = build_redundancy_groups(board, pairs, exposure_watch_set)
    review = build_review_board(board, exposure, representative_map, redundant_factors, config.rules)
    oos_candidates = review[review["review_action"].isin(["oos_extension_candidate", "redundancy_representative_review"])].copy()
    contract = build_contract_status(review, pairs, groups, exposure_watch, oos_candidates, config.rules)

    review.to_csv(config.output_dir / "probe_review_board.csv", index=False, encoding="utf-8-sig")
    pairs.to_csv(config.output_dir / "redundancy_pairs.csv", index=False, encoding="utf-8-sig")
    groups.to_csv(config.output_dir / "redundancy_groups.csv", index=False, encoding="utf-8-sig")
    exposure_watch.to_csv(config.output_dir / "tradability_exposure_watchlist.csv", index=False, encoding="utf-8-sig")
    oos_candidates.to_csv(config.output_dir / "oos_extension_candidates.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(config.output_dir / "probe_review_contract_status.csv", index=False, encoding="utf-8-sig")
    write_report(config, review, pairs, groups, exposure_watch, oos_candidates, contract)
    return {
        "review_board": review,
        "redundancy_pairs": pairs,
        "redundancy_groups": groups,
        "tradability_exposure_watchlist": exposure_watch,
        "oos_extension_candidates": oos_candidates,
        "contract_status": contract,
    }
