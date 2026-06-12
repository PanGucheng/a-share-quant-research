import argparse
from pathlib import Path

import pandas as pd


SUMMARY_COLUMNS = [
    "name",
    "window_start",
    "window_end",
    "label",
    "rebalance_every",
    "topk",
    "weight_preset",
    "score_weights",
    "cost_bps",
    "net_annualized_return",
    "universe_annualized_return",
    "net_annualized_excess",
    "net_excess_ir",
    "net_max_drawdown",
    "average_turnover",
    "max_turnover",
    "skipped_rebalance_rate",
    "average_eligible_count",
    "executed_rebalances",
]


GATE_COST_BPS = 10.0
MAX_TURNOVER = 0.35
MIN_MAIN_NET_EXCESS_IR = 0.30
MIN_OOS_NET_EXCESS_IR = -0.20


def format_float(value) -> str:
    return "" if pd.isna(value) else f"{value:.6f}"


def load_summaries(root: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(root.glob("*/summary.csv")):
        frame = pd.read_csv(path)
        if frame.empty:
            continue
        row = frame.iloc[0].to_dict()
        row["name"] = path.parent.name
        rows.append(row)
    return pd.DataFrame(rows)


def write_markdown(frame: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    display = frame[SUMMARY_COLUMNS].sort_values(
        ["window_start", "label", "cost_bps", "net_excess_ir"], ascending=[True, True, True, False]
    )
    gate = build_gate_check(frame)
    lines = [
        "# Low Frequency Tradability Portfolio Comparison",
        "",
        "Scope:",
        "",
        "```text",
        "market: all_stock_shsz_liquid2000",
        "filters: can_buy, liquidity_bucket >= 3, tradability_score >= 75",
        "capacity: eligible_count >= topk * 2",
        "execution: signal date factors, buy next close, hold 10/20 trading days",
        "```",
        "",
        "## Results",
        "",
        "| name | window | label | rebalance | topk | preset | cost_bps | net_ann_return | universe_ann_return | net_ann_excess | net_excess_ir | max_drawdown | avg_turnover | skipped_rate | avg_eligible | executed |",
        "| --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in display.itertuples(index=False):
        lines.append(
            "| {name} | {window_start} to {window_end} | {label} | {rebalance} | {topk} | {preset} | {cost} | {net_return} | {universe_return} | {net_excess} | {net_ir} | {drawdown} | {turnover} | {skipped} | {eligible} | {executed} |".format(
                name=row.name,
                window_start=row.window_start,
                window_end=row.window_end,
                label=row.label,
                rebalance=int(row.rebalance_every),
                topk=int(row.topk),
                preset=row.weight_preset,
                cost=format_float(row.cost_bps),
                net_return=format_float(row.net_annualized_return),
                universe_return=format_float(row.universe_annualized_return),
                net_excess=format_float(row.net_annualized_excess),
                net_ir=format_float(row.net_excess_ir),
                drawdown=format_float(row.net_max_drawdown),
                turnover=format_float(row.average_turnover),
                skipped=format_float(row.skipped_rebalance_rate),
                eligible=format_float(row.average_eligible_count),
                executed=int(row.executed_rebalances),
            )
        )

    lines.extend(
        [
            "",
            "## Gate Check",
            "",
            f"Gate uses `cost_bps={GATE_COST_BPS:g}`, main window net excess IR >= `{MIN_MAIN_NET_EXCESS_IR:.2f}`, OOS net excess IR >= `{MIN_OOS_NET_EXCESS_IR:.2f}`, and average turnover <= `{MAX_TURNOVER:.2f}`.",
            "",
            "| label | topk | preset | main_net_excess | main_ir | main_turnover | oos_net_excess | oos_ir | oos_turnover | decision |",
            "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in gate.itertuples(index=False):
        lines.append(
            "| {label} | {topk} | {preset} | {main_excess} | {main_ir} | {main_turnover} | {oos_excess} | {oos_ir} | {oos_turnover} | {decision} |".format(
                label=row.label,
                topk=int(row.topk),
                preset=row.weight_preset,
                main_excess=format_float(row.main_net_annualized_excess),
                main_ir=format_float(row.main_net_excess_ir),
                main_turnover=format_float(row.main_average_turnover),
                oos_excess=format_float(row.oos_net_annualized_excess),
                oos_ir=format_float(row.oos_net_excess_ir),
                oos_turnover=format_float(row.oos_average_turnover),
                decision=row.decision,
            )
        )

    best = display.sort_values("net_excess_ir", ascending=False).head(10)
    lines.extend(
        [
            "",
            "## Top 10 By Net Excess IR",
            "",
            "| name | label | cost_bps | net_ann_excess | net_excess_ir | avg_turnover |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in best.itertuples(index=False):
        lines.append(
            f"| {row.name} | {row.label} | {format_float(row.cost_bps)} | {format_float(row.net_annualized_excess)} | {format_float(row.net_excess_ir)} | {format_float(row.average_turnover)} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Template",
            "",
            "- Promote only combinations with positive 2021-2023 net excess and non-negative 2024-2026 net excess at 10 bps.",
            "- Reject combinations whose average turnover is above 0.35 for the personal-investor route.",
            "- If 2024-2026 weakens materially, return to factor engineering instead of adding models.",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_gate_check(frame: pd.DataFrame) -> pd.DataFrame:
    cost_frame = frame[pd.to_numeric(frame["cost_bps"], errors="coerce").eq(GATE_COST_BPS)].copy()
    main = cost_frame[cost_frame["window_start"].eq("2021-01-01")]
    oos = cost_frame[cost_frame["window_start"].eq("2024-01-01")]
    keys = ["label", "topk", "weight_preset"]
    merged = main.merge(oos, on=keys, how="inner", suffixes=("_main", "_oos"))
    rows = []
    for row in merged.itertuples(index=False):
        main_ir = float(row.net_excess_ir_main)
        oos_ir = float(row.net_excess_ir_oos)
        main_turnover = float(row.average_turnover_main)
        oos_turnover = float(row.average_turnover_oos)
        main_excess = float(row.net_annualized_excess_main)
        oos_excess = float(row.net_annualized_excess_oos)
        passed = (
            main_excess > 0
            and main_ir >= MIN_MAIN_NET_EXCESS_IR
            and oos_excess >= 0
            and oos_ir >= MIN_OOS_NET_EXCESS_IR
            and max(main_turnover, oos_turnover) <= MAX_TURNOVER
        )
        decision = "promote" if passed else "reject"
        if decision == "reject":
            reasons = []
            if main_excess <= 0 or main_ir < MIN_MAIN_NET_EXCESS_IR:
                reasons.append("weak_main")
            if oos_excess < 0 or oos_ir < MIN_OOS_NET_EXCESS_IR:
                reasons.append("weak_oos")
            if max(main_turnover, oos_turnover) > MAX_TURNOVER:
                reasons.append("high_turnover")
            decision = "reject:" + ",".join(reasons)
        rows.append(
            {
                "label": row.label,
                "topk": row.topk,
                "weight_preset": row.weight_preset,
                "main_net_annualized_excess": main_excess,
                "main_net_excess_ir": main_ir,
                "main_average_turnover": main_turnover,
                "oos_net_annualized_excess": oos_excess,
                "oos_net_excess_ir": oos_ir,
                "oos_average_turnover": oos_turnover,
                "decision": decision,
            }
        )
    return pd.DataFrame(rows).sort_values(["decision", "main_net_excess_ir"], ascending=[True, False])


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize low-frequency tradability portfolio scans.")
    parser.add_argument("--root", default="outputs/low_frequency_tradability_portfolio")
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    frame = load_summaries(Path(args.root))
    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    frame[SUMMARY_COLUMNS].sort_values(
        ["window_start", "label", "cost_bps", "net_excess_ir"], ascending=[True, True, True, False]
    ).to_csv(output_csv, index=False, encoding="utf-8-sig")
    write_markdown(frame, Path(args.output_md))
    print(f"Wrote low-frequency portfolio comparison to {args.output_md}")


if __name__ == "__main__":
    main()
