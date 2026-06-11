import argparse
import csv
from pathlib import Path

import pandas as pd


def format_float(value) -> str:
    return "" if pd.isna(value) else f"{value:.6f}"


def load_summary(path: Path, market: str, label: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame.insert(0, "label", label)
    frame.insert(0, "market", market)
    return frame


def write_markdown(frame: pd.DataFrame, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    display = frame[
        [
            "market",
            "label",
            "factor",
            "category",
            "expected_direction",
            "coverage",
            "mean_rank_ic",
            "directional_mean_rank_ic",
            "rank_icir",
            "mean_ic",
            "icir",
            "valid_rows",
        ]
    ].copy()
    display = display.sort_values(
        ["market", "label", "mean_rank_ic"],
        key=lambda s: s.abs() if s.name == "mean_rank_ic" else s,
        ascending=[True, True, False],
    )

    lines = [
        "# Factor Label Comparison",
        "",
        "| market | label | factor | category | expected_direction | coverage | mean_rank_ic | directional_mean_rank_ic | rank_icir | mean_ic | icir | valid_rows |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in display.itertuples(index=False):
        lines.append(
            "| {market} | {label} | {factor} | {category} | {expected_direction} | {coverage} | {mean_rank_ic} | {directional_mean_rank_ic} | {rank_icir} | {mean_ic} | {icir} | {valid_rows} |".format(
                market=row.market,
                label=row.label,
                factor=row.factor,
                category=row.category,
                expected_direction=row.expected_direction,
                coverage=format_float(row.coverage),
                mean_rank_ic=format_float(row.mean_rank_ic),
                directional_mean_rank_ic=format_float(row.directional_mean_rank_ic),
                rank_icir=format_float(row.rank_icir),
                mean_ic=format_float(row.mean_ic),
                icir=format_float(row.icir),
                valid_rows=row.valid_rows,
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `label_5d_t1` strengthens the negative relationship for volatility/range and medium-term momentum factors.",
            "- `rev_5` remains positive in both universes, but it is stronger on the one-day label than the five-day label.",
            "- `all_stock_shsz_liquid2000` generally shows stronger factor separation than `csi500` for this simple factor set.",
            "- Raw liquidity factors are better treated as universe/tradability filters than standalone positive alpha signals.",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Summarize factor_summary.csv files across markets and labels.")
    parser.add_argument("--item", action="append", required=True, help="market,label,path_to_factor_summary_csv")
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    frames = []
    for item in args.item:
        market, label, path = item.split(",", 2)
        frames.append(load_summary(Path(path), market, label))
    combined = pd.concat(frames, ignore_index=True)

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_csv, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    write_markdown(combined, Path(args.output_md))
    print(f"Wrote factor comparison to {args.output_md}")


if __name__ == "__main__":
    main()
