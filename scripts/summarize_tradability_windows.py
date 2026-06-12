import argparse
from pathlib import Path

import pandas as pd


SUMMARY_METRICS = [
    "rows",
    "instruments",
    "dates",
    "can_buy_rate",
    "can_sell_rate",
    "avg_tradability_score",
    "is_suspended_rate",
    "is_limit_up_rate",
    "is_limit_down_rate",
    "is_low_liquidity_rate",
    "has_core_missing_rate",
]


def format_float(value) -> str:
    value = pd.to_numeric(value, errors="coerce")
    return "" if pd.isna(value) else f"{value:.6f}"


def load_summary(item: str) -> dict:
    name, path = item.split(",", 1)
    summary = pd.read_csv(Path(path) / "summary.csv")
    values = dict(summary.values.tolist())
    values["window"] = name
    return values


def write_markdown(frame: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Tradability Window Comparison",
        "",
        "| window | rows | instruments | dates | can_buy_rate | can_sell_rate | avg_score | suspended_rate | limit_up_rate | limit_down_rate | low_liquidity_rate | core_missing_rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in frame.itertuples(index=False):
        lines.append(
            "| {window} | {rows} | {instruments} | {dates} | {can_buy} | {can_sell} | {score} | {suspended} | {limit_up} | {limit_down} | {low_liq} | {core_missing} |".format(
                window=row.window,
                rows=int(row.rows),
                instruments=int(row.instruments),
                dates=int(row.dates),
                can_buy=format_float(row.can_buy_rate),
                can_sell=format_float(row.can_sell_rate),
                score=format_float(row.avg_tradability_score),
                suspended=format_float(row.is_suspended_rate),
                limit_up=format_float(row.is_limit_up_rate),
                limit_down=format_float(row.is_limit_down_rate),
                low_liq=format_float(row.is_low_liquidity_rate),
                core_missing=format_float(row.has_core_missing_rate),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The two windows have similar buyable coverage and liquidity-filter impact.",
            "- Low liquidity remains the dominant exclusion reason, so factor portfolios should keep `liquidity_bucket >= 3` as a default constraint.",
            "- Warm-up dates with zero buyable instruments should be skipped by portfolio experiments.",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare tradability output windows.")
    parser.add_argument("--item", action="append", required=True, help="name,path_to_tradability_output_dir")
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    frame = pd.DataFrame([load_summary(item) for item in args.item])
    columns = ["window", *SUMMARY_METRICS]
    for column in SUMMARY_METRICS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    frame[columns].to_csv(output_csv, index=False, encoding="utf-8-sig")
    write_markdown(frame[columns], Path(args.output_md))
    print(f"Wrote tradability window comparison to {args.output_md}")


if __name__ == "__main__":
    main()
