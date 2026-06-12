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
from scripts.run_factor_score_portfolio import add_score, markdown_table, parse_weights


TRADING_DAYS = 252
DEFAULT_WEIGHTS = "std_20:-1,amplitude_20:-1"


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


def load_tradability(tradability_dir: Path) -> pd.DataFrame:
    path = tradability_dir / "tradability_labels.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing tradability_labels.csv: {path}")
    labels = pd.read_csv(path, parse_dates=["datetime"])
    required = ["datetime", "instrument", "can_buy", "can_sell", "liquidity_bucket", "tradability_score"]
    missing = [column for column in required if column not in labels.columns]
    if missing:
        raise ValueError(f"tradability_labels.csv missing required columns: {missing}")
    labels["instrument"] = labels["instrument"].astype(str).str.upper()
    labels["can_buy"] = labels["can_buy"].astype(bool)
    labels["can_sell"] = labels["can_sell"].astype(bool)
    return labels[required]


def prepare_frame(config: FactorResearchConfig, tradability_dir: Path, weights: dict[str, float], clip: float) -> pd.DataFrame:
    raw = load_feature_frame(config)
    factors = add_basic_factors(raw)
    scored = add_score(factors, weights, clip)
    tradability = load_tradability(tradability_dir)
    scored["instrument"] = scored["instrument"].astype(str).str.upper()
    scored = scored.merge(tradability, on=["datetime", "instrument"], how="left")
    scored["can_buy"] = scored["can_buy"].fillna(False).astype(bool)
    scored["can_sell"] = scored["can_sell"].fillna(False).astype(bool)
    scored["liquidity_bucket"] = pd.to_numeric(scored["liquidity_bucket"], errors="coerce")
    scored["tradability_score"] = pd.to_numeric(scored["tradability_score"], errors="coerce")
    scored["daily_return"] = scored.groupby("instrument")["$close"].pct_change(fill_method=None)
    return scored.sort_values(["datetime", "instrument"]).reset_index(drop=True)


def eligible_universe(frame: pd.DataFrame, min_liquidity_bucket: int, min_tradability_score: float) -> pd.DataFrame:
    return frame[
        frame["can_buy"]
        & frame["liquidity_bucket"].ge(min_liquidity_bucket)
        & frame["tradability_score"].ge(min_tradability_score)
    ].copy()


def select_holdings(
    signal_frame: pd.DataFrame,
    topk: int,
    min_liquidity_bucket: int,
    min_tradability_score: float,
    label: str,
) -> tuple[pd.DataFrame, int]:
    candidates = eligible_universe(signal_frame, min_liquidity_bucket, min_tradability_score)
    valid = finite_numeric_rows(candidates, ["instrument", "score", label])
    candidates = candidates.loc[valid.index]
    return candidates.sort_values("score", ascending=False).head(topk), int(len(candidates))


def summarize_daily(daily: pd.DataFrame, rebalances: pd.DataFrame) -> dict:
    if daily.empty:
        return {
            "trading_days": 0,
            "rebalance_count": 0,
            "executed_rebalances": 0,
            "skipped_rebalances": int(len(rebalances)),
        }
    executed = rebalances[rebalances["status"] == "executed"]
    skipped = rebalances[rebalances["status"] != "executed"]
    return {
        "start_date": str(daily["datetime"].min().date()),
        "end_date": str(daily["datetime"].max().date()),
        "trading_days": int(len(daily)),
        "rebalance_count": int(len(rebalances)),
        "executed_rebalances": int(len(executed)),
        "skipped_rebalances": int(len(skipped)),
        "skipped_rebalance_rate": float(len(skipped) / len(rebalances)) if len(rebalances) else np.nan,
        "gross_annualized_return": annualized_return(daily["gross_return"]),
        "net_annualized_return": annualized_return(daily["net_return"]),
        "universe_annualized_return": annualized_return(daily["universe_return"]),
        "gross_annualized_excess": annualized_return(daily["excess_return"]),
        "net_annualized_excess": annualized_return(daily["net_excess_return"]),
        "gross_excess_ir": annualized_ir(daily["excess_return"]),
        "net_excess_ir": annualized_ir(daily["net_excess_return"]),
        "net_max_drawdown": max_drawdown(daily["net_return"]),
        "average_turnover": float(executed["turnover"].mean()) if not executed.empty else np.nan,
        "max_turnover": float(executed["turnover"].max()) if not executed.empty else np.nan,
        "average_eligible_count": float(executed["eligible_count"].mean()) if not executed.empty else np.nan,
        "average_selected_count": float(executed["selected_count"].mean()) if not executed.empty else np.nan,
    }


def run_low_frequency_portfolio(
    frame: pd.DataFrame,
    label: str,
    topk: int,
    rebalance_every: int,
    cost_bps: float,
    min_liquidity_bucket: int,
    min_tradability_score: float,
    min_capacity_multiple: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    dates = pd.Index(sorted(frame["datetime"].dropna().unique()))
    daily_rows = []
    rebalance_rows = []
    position_rows = []
    previous: set[str] | None = None
    cost_rate = cost_bps / 10000
    min_eligible = int(np.ceil(topk * min_capacity_multiple))

    for signal_idx in range(0, len(dates), rebalance_every):
        signal_date = dates[signal_idx]
        execution_idx = signal_idx + 1
        period_end_idx = signal_idx + rebalance_every + 1
        if period_end_idx >= len(dates):
            rebalance_rows.append(
                {
                    "signal_date": signal_date,
                    "status": "skipped_insufficient_future_dates",
                    "eligible_count": 0,
                    "selected_count": 0,
                    "turnover": np.nan,
                }
            )
            continue

        signal_frame = frame[frame["datetime"] == signal_date]
        selected, eligible_count = select_holdings(
            signal_frame, topk, min_liquidity_bucket, min_tradability_score, label
        )
        if eligible_count < min_eligible or len(selected) < topk:
            rebalance_rows.append(
                {
                    "signal_date": signal_date,
                    "status": "skipped_insufficient_eligible_count",
                    "eligible_count": eligible_count,
                    "selected_count": int(len(selected)),
                    "turnover": np.nan,
                }
            )
            continue

        current = set(selected["instrument"])
        turnover = 1.0 if previous is None else 1 - len(current & previous) / topk
        cost = turnover * cost_rate
        selected_instruments = selected["instrument"].tolist()
        eligible_instruments = eligible_universe(signal_frame, min_liquidity_bucket, min_tradability_score)[
            "instrument"
        ].tolist()
        period_dates = dates[execution_idx + 1 : period_end_idx + 1]
        period_rows = []
        for offset, return_date in enumerate(period_dates):
            return_frame = frame[frame["datetime"] == return_date]
            holding_returns = return_frame[return_frame["instrument"].isin(selected_instruments)]["daily_return"].dropna()
            universe_returns = return_frame[return_frame["instrument"].isin(eligible_instruments)]["daily_return"].dropna()
            if holding_returns.empty or universe_returns.empty:
                continue
            gross_return = float(holding_returns.mean())
            daily_cost = cost if offset == 0 else 0.0
            universe_return = float(universe_returns.mean())
            period_rows.append(
                {
                    "datetime": return_date,
                    "signal_date": signal_date,
                    "gross_return": gross_return,
                    "turnover": turnover if offset == 0 else 0.0,
                    "cost": daily_cost,
                    "net_return": gross_return - daily_cost,
                    "universe_return": universe_return,
                    "excess_return": gross_return - universe_return,
                    "net_excess_return": gross_return - daily_cost - universe_return,
                }
            )

        if not period_rows:
            rebalance_rows.append(
                {
                    "signal_date": signal_date,
                    "status": "skipped_no_return_rows",
                    "eligible_count": eligible_count,
                    "selected_count": int(len(selected)),
                    "turnover": turnover,
                }
            )
            continue

        daily_rows.extend(period_rows)
        period_frame = pd.DataFrame(period_rows)
        rebalance_rows.append(
            {
                "signal_date": signal_date,
                "execution_date": dates[execution_idx],
                "period_end_date": period_dates[-1],
                "status": "executed",
                "eligible_count": eligible_count,
                "selected_count": int(len(selected)),
                "turnover": turnover,
                "cost": cost,
                "period_net_return": float((1 + period_frame["net_return"]).prod() - 1),
                "period_universe_return": float((1 + period_frame["universe_return"]).prod() - 1),
                "period_net_excess_return": float((1 + period_frame["net_excess_return"]).prod() - 1),
                "avg_selected_liquidity_bucket": float(selected["liquidity_bucket"].mean()),
                "avg_selected_tradability_score": float(selected["tradability_score"].mean()),
            }
        )
        position_rows.extend(
            {
                "signal_date": signal_date,
                "instrument": row.instrument,
                "score": row.score,
                "liquidity_bucket": row.liquidity_bucket,
                "tradability_score": row.tradability_score,
            }
            for row in selected.itertuples(index=False)
        )
        previous = current

    daily = pd.DataFrame(daily_rows)
    rebalances = pd.DataFrame(rebalance_rows)
    positions = pd.DataFrame(position_rows)
    summary = summarize_daily(daily, rebalances)
    summary.update(
        {
            "label": label,
            "topk": topk,
            "rebalance_every": rebalance_every,
            "cost_bps": cost_bps,
            "min_liquidity_bucket": min_liquidity_bucket,
            "min_tradability_score": min_tradability_score,
            "min_capacity_multiple": min_capacity_multiple,
        }
    )
    return daily, rebalances, positions, summary


def write_report(
    config: FactorResearchConfig,
    weights: dict[str, float],
    summary: dict,
    daily: pd.DataFrame,
    rebalances: pd.DataFrame,
    output: Path,
) -> None:
    lines = [
        "# Low Frequency Tradability Portfolio Report",
        "",
        f"- Provider URI: `{config.provider_uri}`",
        f"- Market: `{config.market}`",
        f"- Date range: `{config.start_time}` to `{config.end_time}`",
        f"- Label: `{summary.get('label')}`",
        f"- Rebalance every: `{summary.get('rebalance_every')}` trading days",
        f"- TopK: `{summary.get('topk')}`",
        f"- Cost: `{summary.get('cost_bps')}` bps per one-way turnover",
        f"- Score weights: `{','.join(f'{name}:{value:g}' for name, value in weights.items())}`",
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
            "- `daily_returns.csv`",
            "- `rebalance_summary.csv`",
            "- `summary.csv`",
            "- `positions.csv`",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(
    output_dir: Path,
    config: FactorResearchConfig,
    weights: dict[str, float],
    daily: pd.DataFrame,
    rebalances: pd.DataFrame,
    positions: pd.DataFrame,
    summary: dict,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    daily.to_csv(output_dir / "daily_returns.csv", index=False, encoding="utf-8-sig")
    rebalances.to_csv(output_dir / "rebalance_summary.csv", index=False, encoding="utf-8-sig")
    positions.to_csv(output_dir / "positions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([summary]).to_csv(output_dir / "summary.csv", index=False, encoding="utf-8-sig")
    write_report(config, weights, summary, daily, rebalances, output_dir / "portfolio_report.md")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a low-frequency tradability-aware factor portfolio.")
    parser.add_argument("--provider-uri", default="E:/qlib_prj/qlib_data/cn_data_community_20260609_derived")
    parser.add_argument("--market", default="all_stock_shsz_liquid2000")
    parser.add_argument("--start-time", required=True)
    parser.add_argument("--end-time", required=True)
    parser.add_argument("--label", default="label_20d_t1")
    parser.add_argument("--tradability-dir", required=True)
    parser.add_argument("--rebalance-every", type=int, default=20)
    parser.add_argument("--topk", type=int, default=200)
    parser.add_argument("--weights", default=DEFAULT_WEIGHTS)
    parser.add_argument("--cost-bps", type=float, default=10.0)
    parser.add_argument("--clip", type=float, default=3.0)
    parser.add_argument("--min-liquidity-bucket", type=int, default=3)
    parser.add_argument("--min-tradability-score", type=float, default=75.0)
    parser.add_argument("--min-capacity-multiple", type=float, default=2.0)
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
    frame = prepare_frame(config, Path(args.tradability_dir), weights, args.clip)
    daily, rebalances, positions, summary = run_low_frequency_portfolio(
        frame,
        args.label,
        args.topk,
        args.rebalance_every,
        args.cost_bps,
        args.min_liquidity_bucket,
        args.min_tradability_score,
        args.min_capacity_multiple,
    )
    summary["score_weights"] = ",".join(f"{factor}:{weight:g}" for factor, weight in weights.items())
    write_outputs(Path(args.output_dir), config, weights, daily, rebalances, positions, summary)
    print(f"Wrote low-frequency portfolio outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
