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
from scripts.run_factor_score_portfolio import (
    DEFAULT_WEIGHTS,
    add_score,
    markdown_table,
    parse_weights,
    summarize_daily,
)


def assign_liquidity_bucket(values: pd.Series, buckets: int) -> pd.Series:
    try:
        return pd.qcut(values, buckets, labels=False, duplicates="drop") + 1
    except ValueError:
        return pd.Series(np.nan, index=values.index)


def select_bucket_balanced(group: pd.DataFrame, topk: int, buckets: int) -> pd.DataFrame:
    group = group.dropna(subset=["liquidity_bucket"])
    if group.empty:
        return group
    per_bucket = max(1, topk // buckets)
    remainder = max(0, topk - per_bucket * buckets)
    selected = []
    for bucket, bucket_frame in group.groupby("liquidity_bucket", sort=True):
        take = per_bucket + (1 if remainder > 0 else 0)
        remainder = max(0, remainder - 1)
        selected.append(bucket_frame.sort_values("score", ascending=False).head(take))
    result = pd.concat(selected, ignore_index=True) if selected else pd.DataFrame()
    return result.sort_values("score", ascending=False).head(topk)


def select_min_liquidity(group: pd.DataFrame, topk: int, min_bucket: int) -> pd.DataFrame:
    liquid = group[group["liquidity_bucket"] >= min_bucket]
    return liquid.sort_values("score", ascending=False).head(topk)


def exposure_summary(holdings: pd.DataFrame) -> pd.DataFrame:
    if holdings.empty:
        return holdings
    columns = [
        "score",
        "rev_5",
        "std_20",
        "amplitude_20",
        "ret_20",
        "amount_mean_20",
        "volume_ratio_5_20",
        "liquidity_bucket",
    ]
    rows = []
    for dt, group in holdings.groupby("datetime", sort=True):
        row = {"datetime": dt, "holding_count": int(len(group))}
        for column in columns:
            row[f"mean_{column}"] = float(group[column].mean())
        rows.append(row)
    daily = pd.DataFrame(rows)
    summary = {"trading_days": int(len(daily))}
    for column in daily.columns:
        if column != "datetime":
            summary[column] = float(daily[column].mean())
    return pd.DataFrame([summary])


def run_bucket_portfolio(
    frame: pd.DataFrame,
    label: str,
    topk: int,
    buckets: int,
    mode: str,
    min_bucket: int,
    cost_bps: float,
    min_count: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    valid = finite_numeric_rows(frame, ["instrument", "score", "amount_mean_20", label])
    scored = frame.loc[valid.index].copy()
    scored["liquidity_bucket"] = scored.groupby("datetime")["amount_mean_20"].transform(
        lambda values: assign_liquidity_bucket(values, buckets)
    )

    daily_rows = []
    holding_rows = []
    previous: set[str] | None = None
    cost_rate = cost_bps / 10000

    for dt, group in scored.groupby("datetime", sort=True):
        if len(group) < max(topk, min_count):
            continue
        if mode == "bucket_balanced":
            selected = select_bucket_balanced(group, topk, buckets)
        elif mode == "min_liquidity":
            selected = select_min_liquidity(group, topk, min_bucket)
        else:
            selected = group.sort_values("score", ascending=False).head(topk)
        if len(selected) < topk:
            continue
        current = set(selected["instrument"])
        turnover = 1.0 if previous is None else 1 - len(current & previous) / topk
        gross_return = selected[label].mean()
        cost = turnover * cost_rate
        universe_return = group[label].mean()
        daily_rows.append(
            {
                "datetime": dt,
                "holding_count": int(len(selected)),
                "gross_return": gross_return,
                "turnover": turnover,
                "cost": cost,
                "net_return": gross_return - cost,
                "universe_return": universe_return,
                "excess_return": gross_return - universe_return,
                "net_excess_return": gross_return - cost - universe_return,
                "average_liquidity_bucket": selected["liquidity_bucket"].mean(),
                "average_amount_mean_20": selected["amount_mean_20"].mean(),
            }
        )
        holding_rows.extend(selected.to_dict("records"))
        previous = current

    daily = pd.DataFrame(daily_rows)
    holdings = pd.DataFrame(holding_rows)
    exposures = exposure_summary(holdings)
    summary = summarize_daily(daily)
    summary.update(
        {
            "topk": topk,
            "liquidity_buckets": buckets,
            "selection_mode": mode,
            "min_liquidity_bucket": min_bucket,
            "cost_bps": cost_bps,
            "min_count": min_count,
            "average_liquidity_bucket": float(daily["average_liquidity_bucket"].mean()) if not daily.empty else np.nan,
            "average_amount_mean_20": float(daily["average_amount_mean_20"].mean()) if not daily.empty else np.nan,
        }
    )
    return daily, holdings, exposures, summary


def write_report(config, weights: dict[str, float], summary: dict, exposures: pd.DataFrame, daily: pd.DataFrame, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Liquidity Bucket Portfolio Report",
        "",
        f"- Provider URI: `{config.provider_uri}`",
        f"- Market: `{config.market}`",
        f"- Date range: `{config.start_time}` to `{config.end_time}`",
        f"- Label: `{config.label}`",
        f"- Score weights: `{','.join(f'{name}:{value:g}' for name, value in weights.items())}`",
        f"- Selection mode: `{summary.get('selection_mode')}`",
        f"- TopK: `{summary.get('topk')}`",
        f"- Liquidity buckets: `{summary.get('liquidity_buckets')}`",
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
            "## Exposure Summary",
            "",
            markdown_table(exposures),
            "",
            "## First Daily Rows",
            "",
            markdown_table(daily.head(10)),
            "",
            "## Output Files",
            "",
            "- `daily_returns.csv`",
            "- `summary.csv`",
            "- `holding_exposure_summary.csv`",
            "- `holdings.csv`",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Run a liquidity-bucket constrained factor score portfolio.")
    parser.add_argument("--provider-uri", default="E:/qlib_prj/qlib_data/cn_data_community_20260609_derived")
    parser.add_argument("--market", default="all_stock_shsz_liquid2000")
    parser.add_argument("--start-time", default="2017-01-01")
    parser.add_argument("--end-time", default="2020-08-01")
    parser.add_argument("--label", default="label_1d_t1")
    parser.add_argument("--weights", default=DEFAULT_WEIGHTS)
    parser.add_argument("--topk", type=int, default=200)
    parser.add_argument("--liquidity-buckets", type=int, default=5)
    parser.add_argument("--selection-mode", choices=["plain_topk", "bucket_balanced", "min_liquidity"], default="bucket_balanced")
    parser.add_argument("--min-liquidity-bucket", type=int, default=3)
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
    scored = add_score(factors, weights, args.clip)
    daily, holdings, exposures, summary = run_bucket_portfolio(
        scored,
        args.label,
        args.topk,
        args.liquidity_buckets,
        args.selection_mode,
        args.min_liquidity_bucket,
        args.cost_bps,
        args.min_count,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    daily.to_csv(output_dir / "daily_returns.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([summary]).to_csv(output_dir / "summary.csv", index=False, encoding="utf-8-sig")
    exposures.to_csv(output_dir / "holding_exposure_summary.csv", index=False, encoding="utf-8-sig")
    holdings.to_csv(output_dir / "holdings.csv", index=False, encoding="utf-8-sig")
    write_report(config, weights, summary, exposures, daily, output_dir / "liquidity_bucket_portfolio_report.md")
    print(f"Wrote liquidity bucket portfolio outputs to {output_dir}")


if __name__ == "__main__":
    main()
