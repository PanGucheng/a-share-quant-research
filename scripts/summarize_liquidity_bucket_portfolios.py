import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_factor_score_portfolio import markdown_table


SUMMARY_COLUMNS = [
    "name",
    "selection_mode",
    "topk",
    "average_liquidity_bucket",
    "average_amount_mean_20",
    "net_annualized_return",
    "universe_annualized_return",
    "net_annualized_excess",
    "net_excess_ir",
    "net_max_drawdown",
    "average_turnover",
    "average_daily_cost",
    "trading_days",
]


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
        "# Liquidity Bucket Portfolio Comparison",
        "",
        "Scope:",
        "",
        "```text",
        "market: all_stock_shsz_liquid2000",
        "label: label_1d_t1",
        "topk: 200",
        "cost: 5 bps per one-way turnover",
        "score: rev_5:1,std_20:-1,amplitude_20:-1",
        "```",
        "",
        "## Results",
        "",
        markdown_table(display),
        "",
        "## Interpretation",
        "",
        "- Liquidity constraints improve the naive long-only score portfolio, but do not make it profitable yet.",
        "- Excluding the lowest two liquidity buckets is better than forcing equal picks across all liquidity buckets.",
        "- This confirms liquidity exposure is part of the problem, but the next long-only version also needs risk or benchmark-relative controls.",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Summarize liquidity bucket portfolio scans.")
    parser.add_argument("--root", default="outputs/liquidity_bucket_portfolio")
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
    print(f"Wrote liquidity bucket comparison to {args.output_md}")


if __name__ == "__main__":
    main()
