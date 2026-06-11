import argparse
from pathlib import Path

import pandas as pd


SUMMARY_COLUMNS = [
    "name",
    "topk",
    "score_weights",
    "net_annualized_return",
    "universe_annualized_return",
    "net_annualized_excess",
    "net_excess_ir",
    "net_max_drawdown",
    "average_turnover",
    "average_daily_cost",
    "trading_days",
]


def format_float(value) -> str:
    return "" if pd.isna(value) else f"{value:.6f}"


def load_summaries(root: Path) -> pd.DataFrame:
    rows = []
    for summary_path in sorted(root.glob("*/summary.csv")):
        frame = pd.read_csv(summary_path)
        if frame.empty:
            continue
        row = frame.iloc[0].to_dict()
        row["name"] = summary_path.parent.name
        rows.append(row)
    return pd.DataFrame(rows)


def write_markdown(frame: pd.DataFrame, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    display = frame[SUMMARY_COLUMNS].sort_values("net_excess_ir", ascending=False)
    lines = [
        "# Factor Score Portfolio Scan",
        "",
        "Scope:",
        "",
        "```text",
        "label: label_1d_t1",
        "cost: 5 bps per one-way turnover",
        "score normalization: daily cross-sectional 1%/99% winsorized z-score, clipped to +/-3",
        "```",
        "",
        "## Results",
        "",
        "| name | topk | score_weights | net_ann_return | universe_ann_return | net_ann_excess | net_excess_ir | net_max_drawdown | avg_turnover | avg_daily_cost | trading_days |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in display.itertuples(index=False):
        lines.append(
            "| {name} | {topk} | `{weights}` | {net_return} | {universe_return} | {net_excess} | {net_ir} | {mdd} | {turnover} | {cost} | {days} |".format(
                name=row.name,
                topk=int(row.topk),
                weights=row.score_weights,
                net_return=format_float(row.net_annualized_return),
                universe_return=format_float(row.universe_annualized_return),
                net_excess=format_float(row.net_annualized_excess),
                net_ir=format_float(row.net_excess_ir),
                mdd=format_float(row.net_max_drawdown),
                turnover=format_float(row.average_turnover),
                cost=format_float(row.average_daily_cost),
                days=int(row.trading_days),
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The naive score portfolios did not beat their universe benchmark in this first pass.",
            "- `rev_5` has positive one-day Rank IC, but direct TopK selection creates high turnover and weak realized portfolio performance.",
            "- The low-risk-only variant is less poor, but still not enough to be treated as a usable strategy.",
            "- The next iteration should add neutralization/exposure checks and compare quantile long-short behavior before promoting any factor score to a Qlib strategy.",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Summarize factor score portfolio summary.csv files.")
    parser.add_argument("--root", default="outputs/factor_score_portfolio")
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    frame = load_summaries(Path(args.root))
    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    frame[SUMMARY_COLUMNS].sort_values("net_excess_ir", ascending=False).to_csv(
        output_csv, index=False, encoding="utf-8-sig"
    )
    write_markdown(frame, Path(args.output_md))
    print(f"Wrote factor score portfolio scan to {args.output_md}")


if __name__ == "__main__":
    main()
