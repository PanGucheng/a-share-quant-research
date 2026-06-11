import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.evaluator import FactorResearchConfig, finite_numeric_rows, load_feature_frame
from factor_research.factor_library import add_basic_factors


DEFAULT_WEIGHTS = "rev_5:1,std_20:-1,amplitude_20:-1"
TRADING_DAYS = 252


def parse_weights(raw: str) -> dict[str, float]:
    weights = {}
    for item in raw.split(","):
        name, value = item.split(":", 1)
        weights[name.strip()] = float(value)
    if not weights:
        raise ValueError("At least one factor weight is required.")
    return weights


def cross_sectional_zscore(values: pd.Series, clip: float) -> pd.Series:
    lower = values.quantile(0.01)
    upper = values.quantile(0.99)
    clipped = values.clip(lower, upper)
    std = clipped.std()
    if not std or pd.isna(std):
        return pd.Series(np.nan, index=values.index)
    return ((clipped - clipped.mean()) / std).clip(-clip, clip)


def add_score(frame: pd.DataFrame, weights: dict[str, float], clip: float) -> pd.DataFrame:
    required = [*weights.keys()]
    scored = frame.copy()
    scored["score"] = 0.0
    scored["score_component_count"] = 0

    for factor, weight in weights.items():
        column = f"z_{factor}"
        scored[column] = scored.groupby("datetime", group_keys=False)[factor].transform(
            lambda values: cross_sectional_zscore(values, clip)
        )
        mask = scored[column].notna()
        scored.loc[mask, "score"] += scored.loc[mask, column] * weight
        scored.loc[mask, "score_component_count"] += 1

    valid = finite_numeric_rows(scored, ["instrument", "score", "score_component_count", *required])
    return scored.loc[valid.index]


def run_portfolio(
    frame: pd.DataFrame,
    label: str,
    weights: dict[str, float],
    topk: int,
    cost_bps: float,
    clip: float,
    min_count: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    scored = add_score(frame, weights, clip)
    valid = finite_numeric_rows(scored, ["instrument", "score", label])
    scored = scored.loc[valid.index]

    daily_rows = []
    holding_rows = []
    previous: set[str] | None = None
    cost_rate = cost_bps / 10000

    for dt, group in scored.groupby("datetime", sort=True):
        if len(group) < max(topk, min_count):
            continue
        ranked = group.sort_values("score", ascending=False).head(topk)
        current = set(ranked["instrument"])
        turnover = 1.0 if previous is None else 1 - len(current & previous) / topk
        gross_return = ranked[label].mean()
        cost = turnover * cost_rate
        universe_return = group[label].mean()
        daily_rows.append(
            {
                "datetime": dt,
                "holding_count": int(len(ranked)),
                "gross_return": gross_return,
                "turnover": turnover,
                "cost": cost,
                "net_return": gross_return - cost,
                "universe_return": universe_return,
                "excess_return": gross_return - universe_return,
                "net_excess_return": gross_return - cost - universe_return,
            }
        )
        holding_rows.extend(
            {
                "datetime": dt,
                "instrument": row.instrument,
                "score": row.score,
                label: getattr(row, label),
            }
            for row in ranked.itertuples(index=False)
        )
        previous = current

    daily = pd.DataFrame(daily_rows)
    holdings = pd.DataFrame(holding_rows)
    summary = summarize_daily(daily)
    summary.update(
        {
            "topk": topk,
            "cost_bps": cost_bps,
            "score_weights": ",".join(f"{factor}:{weight:g}" for factor, weight in weights.items()),
            "score_clip": clip,
            "min_count": min_count,
        }
    )
    return daily, holdings, summary


def annualized_return(series: pd.Series) -> float:
    if series.empty:
        return np.nan
    return float((1 + series).prod() ** (TRADING_DAYS / len(series)) - 1)


def annualized_ir(series: pd.Series) -> float:
    std = series.std()
    if len(series) < 2 or not std:
        return np.nan
    return float(series.mean() / std * np.sqrt(TRADING_DAYS))


def max_drawdown(series: pd.Series) -> float:
    if series.empty:
        return np.nan
    curve = (1 + series).cumprod()
    return float((curve / curve.cummax() - 1).min())


def summarize_daily(daily: pd.DataFrame) -> dict:
    if daily.empty:
        return {}
    return {
        "start_date": str(daily["datetime"].min().date()),
        "end_date": str(daily["datetime"].max().date()),
        "trading_days": int(len(daily)),
        "gross_annualized_return": annualized_return(daily["gross_return"]),
        "net_annualized_return": annualized_return(daily["net_return"]),
        "universe_annualized_return": annualized_return(daily["universe_return"]),
        "gross_annualized_excess": annualized_return(daily["excess_return"]),
        "net_annualized_excess": annualized_return(daily["net_excess_return"]),
        "gross_excess_ir": annualized_ir(daily["excess_return"]),
        "net_excess_ir": annualized_ir(daily["net_excess_return"]),
        "net_max_drawdown": max_drawdown(daily["net_return"]),
        "average_turnover": float(daily["turnover"].mean()),
        "average_daily_cost": float(daily["cost"].mean()),
    }


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    display = frame.copy()
    for column in display.columns:
        if pd.api.types.is_datetime64_any_dtype(display[column]):
            display[column] = display[column].dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(lambda value: "" if pd.isna(value) else f"{value:.6f}")
    lines = ["| " + " | ".join(display.columns) + " |", "| " + " | ".join(["---"] * len(display.columns)) + " |"]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in display.values.tolist())
    return "\n".join(lines)


def write_report(config, summary: dict, daily: pd.DataFrame, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Factor Score Portfolio Report",
        "",
        f"- Provider URI: `{config.provider_uri}`",
        f"- Market: `{config.market}`",
        f"- Date range: `{config.start_time}` to `{config.end_time}`",
        f"- Label: `{config.label}`",
        f"- Score weights: `{summary.get('score_weights')}`",
        f"- TopK: `{summary.get('topk')}`",
        f"- Cost: `{summary.get('cost_bps')}` bps per one-way turnover",
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
            "## First Daily Rows",
            "",
            markdown_table(daily.head(10)),
            "",
            "## Output Files",
            "",
            "- `daily_returns.csv`",
            "- `summary.csv`",
            "- `holdings.csv`",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Backtest a simple equal-weight factor score portfolio.")
    parser.add_argument("--provider-uri", default="E:/qlib_prj/qlib_data/cn_data_community_20260609_derived")
    parser.add_argument("--market", required=True)
    parser.add_argument("--start-time", default="2017-01-01")
    parser.add_argument("--end-time", default="2020-08-01")
    parser.add_argument("--label", default="label_1d_t1")
    parser.add_argument("--weights", default=DEFAULT_WEIGHTS)
    parser.add_argument("--topk", type=int, required=True)
    parser.add_argument("--cost-bps", type=float, default=5.0)
    parser.add_argument("--clip", type=float, default=3.0)
    parser.add_argument("--min-count", type=int, default=100)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    config = FactorResearchConfig(
        provider_uri=args.provider_uri,
        market=args.market,
        start_time=args.start_time,
        end_time=args.end_time,
        label=args.label,
        output_dir=Path(args.output_dir),
    )
    weights = parse_weights(args.weights)
    raw = load_feature_frame(config)
    factors = add_basic_factors(raw)
    daily, holdings, summary = run_portfolio(
        factors,
        args.label,
        weights,
        args.topk,
        args.cost_bps,
        args.clip,
        args.min_count,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    daily.to_csv(output_dir / "daily_returns.csv", index=False, encoding="utf-8-sig")
    holdings.to_csv(output_dir / "holdings.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([summary]).to_csv(output_dir / "summary.csv", index=False, encoding="utf-8-sig")
    write_report(config, summary, daily, output_dir / "factor_score_portfolio_report.md")
    print(f"Wrote factor score portfolio outputs to {output_dir}")


if __name__ == "__main__":
    main()
