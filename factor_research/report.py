import pandas as pd


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    display = frame.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(lambda value: "" if pd.isna(value) else f"{value:.6f}")
    lines = ["| " + " | ".join(display.columns) + " |", "| " + " | ".join(["---"] * len(display.columns)) + " |"]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in display.values.tolist())
    return "\n".join(lines)


def write_markdown_report(config, summary, ic_series, group_returns, turnover, output):
    top_summary = summary.head(20)
    group_overview = (
        group_returns.groupby(["factor", "quantile"])["mean_label"].mean().reset_index()
        if not group_returns.empty
        else pd.DataFrame()
    )
    turnover_overview = turnover.groupby("factor")["turnover"].mean().reset_index() if not turnover.empty else pd.DataFrame()

    lines = [
        "# Factor Research Report",
        "",
        f"- Provider URI: `{config.provider_uri}`",
        f"- Market: `{config.market}`",
        f"- Date range: `{config.start_time}` to `{config.end_time}`",
        f"- Label: `{config.label}`",
        f"- IC rows: `{len(ic_series)}`",
        "",
        "## Factor Summary",
        "",
        markdown_table(top_summary),
        "",
        "## Average Group Returns",
        "",
        markdown_table(group_overview.head(60)),
        "",
        "## Average Top-Quantile Turnover",
        "",
        markdown_table(turnover_overview),
        "",
        "## Output Files",
        "",
        "- `factor_summary.csv`",
        "- `ic_series.csv`",
        "- `group_return.csv`",
        "- `turnover.csv`",
        "- `correlation.csv`",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
