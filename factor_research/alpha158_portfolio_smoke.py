from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
import pandas as pd

from factor_research.evaluator import FactorResearchConfig, load_feature_frame
from factor_research.factor_library import add_basic_factors
from factor_research.report import markdown_table
from scripts.run_factor_score_portfolio import cross_sectional_zscore
from scripts.run_low_frequency_tradability_portfolio import (
    load_tradability,
    run_low_frequency_portfolio,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_CANDIDATE_COLUMNS = [
    "factor",
    "role",
    "judgement_label",
    "consensus_direction",
    "issue_tags",
    "high_turnover",
    "unstable_context",
    "is_redundant",
]


@dataclass(frozen=True)
class Alpha158PortfolioSmokeConfig:
    candidate_pool: Path
    expression_frame_dir: Path
    tradability_dir: Path
    provider_uri: str
    market: str
    start_time: str
    end_time: str
    label: str
    feature_cache_dir: Path | None
    output_dir: Path
    score_policy: str
    score_clip: float
    min_score_components: int
    rebalance_every: int
    topk: int
    cost_bps: float
    min_liquidity_bucket: int
    min_tradability_score: float
    min_capacity_multiple: float


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


def load_alpha_candidates(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing alpha candidate pool: {path}")
    candidates = pd.read_csv(path)
    missing = [column for column in REQUIRED_CANDIDATE_COLUMNS if column not in candidates.columns]
    if missing:
        raise ValueError(f"candidate pool missing required columns: {missing}")
    if candidates.empty:
        raise ValueError("candidate pool is empty")
    bad_roles = sorted(set(candidates.loc[~candidates["role"].eq("alpha_candidate"), "role"]))
    if bad_roles:
        raise ValueError(f"non-alpha candidate roles found in alpha input: {bad_roles}")
    for column in ["high_turnover", "unstable_context", "is_redundant"]:
        if candidates[column].map(as_bool).any():
            raise ValueError(f"alpha input contains forbidden flag: {column}")
    return candidates.copy()


def candidate_weight_table(candidates: pd.DataFrame, score_policy: str) -> pd.DataFrame:
    if score_policy != "equal_directional_zscore":
        raise ValueError(f"Unsupported score_policy: {score_policy}")
    rows = []
    for row in candidates.itertuples(index=False):
        direction = str(row.consensus_direction)
        if direction == "positive":
            weight = 1.0
        elif direction == "negative":
            weight = -1.0
        else:
            raise ValueError(f"Unsupported consensus_direction for {row.factor}: {direction}")
        rows.append(
            {
                "factor": row.factor,
                "weight": weight,
                "consensus_direction": direction,
                "judgement_label": row.judgement_label,
                "issue_tags": "" if pd.isna(row.issue_tags) else row.issue_tags,
            }
        )
    return pd.DataFrame(rows)


def load_expression_manifest(expression_frame_dir: Path) -> dict:
    path = expression_frame_dir / "expression_frame_manifest.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_expression_table(expression_frame_dir: Path) -> pd.DataFrame:
    path = expression_frame_dir / "expression_table.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing expression_table.csv: {path}")
    table = pd.read_csv(path)
    if "catalog_name" not in table.columns:
        raise ValueError(f"expression_table.csv missing catalog_name: {path}")
    return table


def load_candidate_factor_frame(expression_frame_dir: Path, factors: list[str]) -> pd.DataFrame:
    expression_table = load_expression_table(expression_frame_dir)
    factor_order = expression_table["catalog_name"].astype(str).tolist()
    missing_from_table = sorted(set(factors) - set(factor_order))
    if missing_from_table:
        raise ValueError(f"candidate factors missing from expression table: {missing_from_table}")

    manifest = load_expression_manifest(expression_frame_dir)
    batch_size = int(manifest.get("config", {}).get("batch_size") or 0)
    chunk_paths = sorted(expression_frame_dir.glob("factor_frame_chunk_*.pkl"))
    pieces = []

    if chunk_paths and batch_size > 0:
        for index, chunk_path in enumerate(chunk_paths):
            chunk_factors = factor_order[index * batch_size : (index + 1) * batch_size]
            selected = [factor for factor in factors if factor in chunk_factors]
            if not selected:
                continue
            chunk = pd.read_pickle(chunk_path)
            missing = [factor for factor in selected if factor not in chunk.columns]
            if missing:
                raise ValueError(f"{chunk_path} missing expected factors: {missing}")
            pieces.append(chunk[["datetime", "instrument", *selected]].copy())
    else:
        frame_path = expression_frame_dir / "factor_frame.pkl"
        if not frame_path.exists():
            raise FileNotFoundError(f"Missing factor_frame.pkl and chunk files in {expression_frame_dir}")
        full = pd.read_pickle(frame_path)
        missing = [factor for factor in factors if factor not in full.columns]
        if missing:
            raise ValueError(f"factor_frame.pkl missing candidate factors: {missing}")
        pieces.append(full[["datetime", "instrument", *factors]].copy())

    if not pieces:
        raise ValueError("No candidate factor chunks were loaded")

    merged = pieces[0]
    for piece in pieces[1:]:
        merged = merged.merge(piece, on=["datetime", "instrument"], how="inner")
    missing_from_frame = [factor for factor in factors if factor not in merged.columns]
    if missing_from_frame:
        raise ValueError(f"candidate factors missing from merged frame: {missing_from_frame}")
    merged["datetime"] = pd.to_datetime(merged["datetime"])
    merged["instrument"] = merged["instrument"].astype(str).str.upper()
    return merged


def score_candidates(
    factor_frame: pd.DataFrame,
    weights: pd.DataFrame,
    start_time: str,
    end_time: str,
    clip: float,
    min_score_components: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    start = pd.Timestamp(start_time)
    end = pd.Timestamp(end_time)
    frame = factor_frame[factor_frame["datetime"].between(start, end)].copy()
    if frame.empty:
        raise ValueError(f"candidate factor frame is empty in date range {start_time} to {end_time}")

    score = pd.Series(0.0, index=frame.index)
    total_abs_weight = pd.Series(0.0, index=frame.index)
    component_count = pd.Series(0, index=frame.index, dtype="int64")
    component_rows = []

    for row in weights.itertuples(index=False):
        zscore = frame.groupby("datetime", group_keys=False)[row.factor].transform(
            lambda values: cross_sectional_zscore(values, clip)
        )
        valid = zscore.notna()
        score.loc[valid] += zscore.loc[valid] * row.weight
        total_abs_weight.loc[valid] += abs(row.weight)
        component_count.loc[valid] += 1
        component_rows.append(
            {
                "factor": row.factor,
                "weight": row.weight,
                "valid_rows": int(valid.sum()),
                "coverage": float(valid.mean()),
            }
        )

    frame["score_component_count"] = component_count
    frame["score"] = np.where(total_abs_weight > 0, score / total_abs_weight, np.nan)
    frame = frame[frame["score_component_count"].ge(min_score_components)].copy()
    return frame[["datetime", "instrument", "score", "score_component_count"]], pd.DataFrame(component_rows)


def load_label_frame(config: Alpha158PortfolioSmokeConfig) -> pd.DataFrame:
    feature_config = FactorResearchConfig(
        provider_uri=config.provider_uri,
        market=config.market,
        start_time=config.start_time,
        end_time=config.end_time,
        label=config.label,
        output_dir=config.output_dir,
        feature_cache_dir=config.feature_cache_dir,
    )
    raw = load_feature_frame(feature_config)
    features = add_basic_factors(raw)
    features["instrument"] = features["instrument"].astype(str).str.upper()
    features["datetime"] = pd.to_datetime(features["datetime"])
    features["daily_return"] = features.groupby("instrument")["$close"].pct_change(fill_method=None)
    required = ["datetime", "instrument", config.label, "daily_return"]
    missing = [column for column in required if column not in features.columns]
    if missing:
        raise ValueError(f"feature frame missing required columns: {missing}")
    return features[required].copy()


def build_portfolio_frame(
    score_frame: pd.DataFrame,
    label_frame: pd.DataFrame,
    tradability_dir: Path,
) -> pd.DataFrame:
    frame = score_frame.merge(label_frame, on=["datetime", "instrument"], how="inner")
    tradability = load_tradability(tradability_dir)
    frame = frame.merge(tradability, on=["datetime", "instrument"], how="left")
    frame["can_buy"] = frame["can_buy"].fillna(False).astype(bool)
    frame["can_sell"] = frame["can_sell"].fillna(False).astype(bool)
    frame["liquidity_bucket"] = pd.to_numeric(frame["liquidity_bucket"], errors="coerce")
    frame["tradability_score"] = pd.to_numeric(frame["tradability_score"], errors="coerce")
    return frame.sort_values(["datetime", "instrument"]).reset_index(drop=True)


def summarize_candidate_pool(candidates: pd.DataFrame, weights: pd.DataFrame) -> dict:
    warning_mask = candidates["issue_tags"].fillna("").astype(str).str.contains("low_monotonicity", regex=False)
    return {
        "candidate_count": int(len(candidates)),
        "warning_low_monotonicity_count": int(warning_mask.sum()),
        "positive_direction_count": int(weights["weight"].gt(0).sum()),
        "negative_direction_count": int(weights["weight"].lt(0).sum()),
    }


def write_report(
    config: Alpha158PortfolioSmokeConfig,
    candidates: pd.DataFrame,
    weights: pd.DataFrame,
    component_summary: pd.DataFrame,
    summary: dict,
    daily: pd.DataFrame,
    rebalances: pd.DataFrame,
    output: Path,
) -> None:
    candidate_view = candidates[
        ["factor", "judgement_label", "consensus_direction", "primary_rank_ic", "issue_tags"]
    ].copy()
    candidate_view["issue_tags"] = candidate_view["issue_tags"].fillna("")
    candidate_view["weight"] = candidate_view["factor"].map(weights.set_index("factor")["weight"])
    warning_view = candidate_view[candidate_view["issue_tags"].fillna("").astype(str).str.contains("low_monotonicity")]
    lines = [
        "# Alpha158 Candidate Portfolio Smoke V1",
        "",
        f"- Candidate pool: `{display_path(config.candidate_pool)}`",
        f"- Expression frame: `{display_path(config.expression_frame_dir)}`",
        f"- Tradability dir: `{display_path(config.tradability_dir)}`",
        f"- Market: `{config.market}`",
        f"- Date range: `{config.start_time}` to `{config.end_time}`",
        f"- Label: `{config.label}`",
        f"- Score policy: `{config.score_policy}`",
        f"- Rebalance every: `{config.rebalance_every}` trading days",
        f"- TopK: `{config.topk}`",
        f"- Cost: `{config.cost_bps}` bps per one-way turnover",
        "",
        "## Summary",
        "",
        "| metric | value |",
        "| --- | ---: |",
    ]
    for key, value in summary.items():
        if isinstance(value, float):
            lines.append(f"| {key} | `{value:.6f}` |")
        else:
            lines.append(f"| {key} | `{value}` |")
    lines.extend(
        [
            "",
            "## Candidate Weights",
            "",
            markdown_table(candidate_view),
            "",
            "## Low Monotonicity Warnings",
            "",
            markdown_table(warning_view),
            "",
            "## Score Component Coverage",
            "",
            markdown_table(component_summary),
            "",
            "## First Rebalances",
            "",
            markdown_table(rebalances.head(10)),
            "",
            "## First Daily Rows",
            "",
            markdown_table(daily.head(10)),
            "",
            "## Output Files",
            "",
            "- `summary.csv`",
            "- `daily_returns.csv`",
            "- `rebalance_summary.csv`",
            "- `positions.csv`",
            "- `candidate_weight_table.csv`",
            "- `score_component_summary.csv`",
            "- `alpha158_candidate_portfolio_smoke_report.md`",
            "",
            "## Notes",
            "",
            "- This is an interface smoke test, not a production strategy.",
            "- The input is restricted to `role == alpha_candidate` from the frozen candidate pool.",
            "- Tradability labels are applied before holdings are selected.",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(
    config: Alpha158PortfolioSmokeConfig,
    candidates: pd.DataFrame,
    weights: pd.DataFrame,
    component_summary: pd.DataFrame,
    daily: pd.DataFrame,
    rebalances: pd.DataFrame,
    positions: pd.DataFrame,
    summary: dict,
) -> None:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    daily.to_csv(config.output_dir / "daily_returns.csv", index=False, encoding="utf-8-sig")
    rebalances.to_csv(config.output_dir / "rebalance_summary.csv", index=False, encoding="utf-8-sig")
    positions.to_csv(config.output_dir / "positions.csv", index=False, encoding="utf-8-sig")
    weights.to_csv(config.output_dir / "candidate_weight_table.csv", index=False, encoding="utf-8-sig")
    component_summary.to_csv(config.output_dir / "score_component_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([summary]).to_csv(config.output_dir / "summary.csv", index=False, encoding="utf-8-sig")
    write_report(
        config,
        candidates,
        weights,
        component_summary,
        summary,
        daily,
        rebalances,
        config.output_dir / "alpha158_candidate_portfolio_smoke_report.md",
    )


def run_alpha158_portfolio_smoke(config: Alpha158PortfolioSmokeConfig) -> dict[str, pd.DataFrame | dict]:
    candidates = load_alpha_candidates(config.candidate_pool)
    weights = candidate_weight_table(candidates, config.score_policy)
    factor_frame = load_candidate_factor_frame(config.expression_frame_dir, weights["factor"].tolist())
    score_frame, component_summary = score_candidates(
        factor_frame,
        weights,
        config.start_time,
        config.end_time,
        config.score_clip,
        config.min_score_components,
    )
    label_frame = load_label_frame(config)
    portfolio_frame = build_portfolio_frame(score_frame, label_frame, config.tradability_dir)
    daily, rebalances, positions, summary = run_low_frequency_portfolio(
        portfolio_frame,
        config.label,
        config.topk,
        config.rebalance_every,
        config.cost_bps,
        config.min_liquidity_bucket,
        config.min_tradability_score,
        config.min_capacity_multiple,
    )
    summary.update(
        {
            **summarize_candidate_pool(candidates, weights),
            "score_policy": config.score_policy,
            "score_clip": config.score_clip,
            "min_score_components": config.min_score_components,
        }
    )
    write_outputs(config, candidates, weights, component_summary, daily, rebalances, positions, summary)
    return {
        "daily": daily,
        "rebalances": rebalances,
        "positions": positions,
        "summary": summary,
        "weights": weights,
        "component_summary": component_summary,
    }
