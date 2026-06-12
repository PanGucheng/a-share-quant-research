import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_factor_score_portfolio import markdown_table


SUMMARY_COLUMNS = [
    "market",
    "signal",
    "net_annualized_return",
    "net_ir",
    "net_max_drawdown",
    "average_long_return",
    "average_short_return",
    "average_spread",
    "average_turnover",
    "average_daily_cost",
    "trading_days",
]

EXPOSURE_COLUMNS = [
    "market",
    "signal",
    "spread_mean_label",
    "spread_mean_score",
    "spread_mean_rev_5",
    "spread_mean_std_20",
    "spread_mean_amplitude_20",
    "spread_mean_ret_20",
    "spread_mean_amount_mean_20",
    "spread_mean_volume_ratio_5_20",
]


def infer_market(path: Path) -> str:
    name = path.parent.name
    if name.startswith("all_stock_shsz_liquid2000"):
        return "all_stock_shsz_liquid2000"
    if name.startswith("csi500"):
        return "csi500"
    return name


def load_summaries(root: Path) -> pd.DataFrame:
    rows = []
    for summary_path in sorted(root.glob("*/summary_by_signal.csv")):
        frame = pd.read_csv(summary_path)
        frame.insert(0, "market", infer_market(summary_path))
        rows.append(frame)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=SUMMARY_COLUMNS)


def load_exposures(root: Path) -> pd.DataFrame:
    rows = []
    for exposure_path in sorted(root.glob("*/leg_exposure_summary.csv")):
        frame = pd.read_csv(exposure_path)
        frame.insert(0, "market", infer_market(exposure_path))
        rows.append(frame)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=EXPOSURE_COLUMNS)


def write_markdown(frame: pd.DataFrame, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    display = frame[SUMMARY_COLUMNS].sort_values(["market", "net_ir"], ascending=[True, False])
    lines = [
        "# Factor Long-Short Comparison",
        "",
        "Scope:",
        "",
        "```text",
        "label: label_1d_t1",
        "quantile: top 20% long, bottom 20% short",
        "cost: 5 bps per one-way turnover",
        "```",
        "",
        "## Results",
        "",
        markdown_table(display),
        "",
        "## Interpretation",
        "",
        "- Long-short diagnostics are positive while the earlier long-only TopK portfolios are negative.",
        "- This means the factor ranking has signal, but naive long-only construction is absorbing unfavorable exposure.",
        "- Low volatility and low amplitude are the most stable signals in this pass.",
        "- The next step should inspect long-leg and short-leg exposures, then design a long-only portfolio with benchmark or risk controls.",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_exposure_markdown(frame: pd.DataFrame, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    available_columns = [column for column in EXPOSURE_COLUMNS if column in frame.columns]
    display = frame[available_columns].sort_values(["market", "signal"]) if not frame.empty else frame
    lines = [
        "# Factor Long-Short Exposure Comparison",
        "",
        "Positive spread means the long leg has a higher average value than the short leg.",
        "",
        "## Exposure Spreads",
        "",
        markdown_table(display),
        "",
        "## Interpretation",
        "",
        "- `spread_mean_label` is the realized long-minus-short label spread and should align with the long-short return report.",
        "- Large `spread_mean_std_20` or `spread_mean_amplitude_20` gaps show whether the signal is mostly a risk sort.",
        "- Large liquidity gaps mean a long-only version may need liquidity buckets before selecting names.",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Summarize factor long-short diagnostics.")
    parser.add_argument("--root", default="outputs/factor_long_short")
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--exposure-output-csv")
    parser.add_argument("--exposure-output-md")
    args = parser.parse_args()

    frame = load_summaries(Path(args.root))
    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    frame[SUMMARY_COLUMNS].sort_values(["market", "net_ir"], ascending=[True, False]).to_csv(
        output_csv, index=False, encoding="utf-8-sig"
    )
    write_markdown(frame, Path(args.output_md))
    if args.exposure_output_csv and args.exposure_output_md:
        exposure = load_exposures(Path(args.root))
        exposure_csv = Path(args.exposure_output_csv)
        exposure_csv.parent.mkdir(parents=True, exist_ok=True)
        available_columns = [column for column in EXPOSURE_COLUMNS if column in exposure.columns]
        exposure[available_columns].sort_values(["market", "signal"]).to_csv(
            exposure_csv, index=False, encoding="utf-8-sig"
        )
        write_exposure_markdown(exposure, Path(args.exposure_output_md))
    print(f"Wrote factor long-short comparison to {args.output_md}")


if __name__ == "__main__":
    main()
