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
    annualized_ir,
    annualized_return,
    markdown_table,
    max_drawdown,
    parse_weights,
)


DEFAULT_SIGNALS = "rev_5:1,std_20:-1,amplitude_20:-1,score:1"


def parse_signals(raw: str) -> dict[str, float]:
    signals = {}
    for item in raw.split(","):
        name, value = item.split(":", 1)
        signals[name.strip()] = float(value)
    if not signals:
        raise ValueError("At least one signal is required.")
    return signals


def add_weighted_score(frame: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    scored = frame.copy()
    scored["score"] = 0.0
    for factor, weight in weights.items():
        valid = finite_numeric_rows(scored, ["instrument", factor])
        factor_values = scored.loc[valid.index].groupby("datetime")[factor]
        zscore = factor_values.transform(lambda values: (values - values.mean()) / values.std() if values.std() else np.nan)
        scored.loc[zscore.index, "score"] += zscore.clip(-3, 3) * weight
    return scored


def summarize_long_short(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for signal, group in daily.groupby("signal", sort=True):
        rows.append(
            {
                "signal": signal,
                "start_date": str(group["datetime"].min().date()),
                "end_date": str(group["datetime"].max().date()),
                "trading_days": int(len(group)),
                "gross_annualized_return": annualized_return(group["gross_long_short_return"]),
                "net_annualized_return": annualized_return(group["net_long_short_return"]),
                "gross_ir": annualized_ir(group["gross_long_short_return"]),
                "net_ir": annualized_ir(group["net_long_short_return"]),
                "net_max_drawdown": max_drawdown(group["net_long_short_return"]),
                "average_long_return": float(group["long_return"].mean()),
                "average_short_return": float(group["short_return"].mean()),
                "average_spread": float(group["gross_long_short_return"].mean()),
                "average_turnover": float(group["turnover"].mean()),
                "average_daily_cost": float(group["cost"].mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("net_ir", ascending=False)


def run_long_short(
    frame: pd.DataFrame,
    label: str,
    signals: dict[str, float],
    quantile: float,
    cost_bps: float,
    min_count: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    daily_rows = []
    cost_rate = cost_bps / 10000

    for signal, direction in signals.items():
        previous_long: set[str] | None = None
        previous_short: set[str] | None = None
        signed_signal = f"signed_{signal}"
        frame[signed_signal] = frame[signal] * direction

        for dt, group in frame.groupby("datetime", sort=True):
            values = finite_numeric_rows(group, ["instrument", signed_signal, label])
            if len(values) < min_count:
                continue
            side_count = int(len(values) * quantile)
            if side_count < 1:
                continue
            ranked = values.sort_values(signed_signal)
            short_leg = ranked.head(side_count)
            long_leg = ranked.tail(side_count)
            current_long = set(long_leg["instrument"])
            current_short = set(short_leg["instrument"])
            long_turnover = 1.0 if previous_long is None else 1 - len(current_long & previous_long) / side_count
            short_turnover = 1.0 if previous_short is None else 1 - len(current_short & previous_short) / side_count
            turnover = (long_turnover + short_turnover) / 2
            long_return = long_leg[label].mean()
            short_return = short_leg[label].mean()
            gross = long_return - short_return
            cost = turnover * cost_rate
            daily_rows.append(
                {
                    "datetime": dt,
                    "signal": signal,
                    "direction": direction,
                    "side_count": side_count,
                    "long_return": long_return,
                    "short_return": short_return,
                    "gross_long_short_return": gross,
                    "long_turnover": long_turnover,
                    "short_turnover": short_turnover,
                    "turnover": turnover,
                    "cost": cost,
                    "net_long_short_return": gross - cost,
                }
            )
            previous_long = current_long
            previous_short = current_short

    daily = pd.DataFrame(daily_rows)
    return daily, summarize_long_short(daily)


def write_report(config, weights: dict[str, float], signals: dict[str, float], summary: pd.DataFrame, daily: pd.DataFrame, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Factor Long-Short Report",
        "",
        f"- Provider URI: `{config.provider_uri}`",
        f"- Market: `{config.market}`",
        f"- Date range: `{config.start_time}` to `{config.end_time}`",
        f"- Label: `{config.label}`",
        f"- Score weights: `{','.join(f'{name}:{value:g}' for name, value in weights.items())}`",
        f"- Signals: `{','.join(f'{name}:{value:g}' for name, value in signals.items())}`",
        "",
        "## Summary",
        "",
        markdown_table(summary),
        "",
        "## First Daily Rows",
        "",
        markdown_table(daily.head(10)),
        "",
        "## Output Files",
        "",
        "- `daily_long_short.csv`",
        "- `summary_by_signal.csv`",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Run factor quantile long-short diagnostics.")
    parser.add_argument("--provider-uri", default="E:/qlib_prj/qlib_data/cn_data_community_20260609_derived")
    parser.add_argument("--market", required=True)
    parser.add_argument("--start-time", default="2017-01-01")
    parser.add_argument("--end-time", default="2020-08-01")
    parser.add_argument("--label", default="label_1d_t1")
    parser.add_argument("--weights", default=DEFAULT_WEIGHTS)
    parser.add_argument("--signals", default=DEFAULT_SIGNALS)
    parser.add_argument("--quantile", type=float, default=0.2)
    parser.add_argument("--cost-bps", type=float, default=5.0)
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
    signals = parse_signals(args.signals)
    raw = load_feature_frame(config)
    factors = add_basic_factors(raw)
    scored = add_weighted_score(factors, weights)
    daily, summary = run_long_short(scored, args.label, signals, args.quantile, args.cost_bps, args.min_count)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    daily.to_csv(output_dir / "daily_long_short.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(output_dir / "summary_by_signal.csv", index=False, encoding="utf-8-sig")
    write_report(config, weights, signals, summary, daily, output_dir / "factor_long_short_report.md")
    print(f"Wrote factor long-short outputs to {output_dir}")


if __name__ == "__main__":
    main()
