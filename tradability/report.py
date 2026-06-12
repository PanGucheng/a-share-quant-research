from pathlib import Path

import pandas as pd


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    display = frame.copy()
    for column in display.columns:
        if pd.api.types.is_datetime64_any_dtype(display[column]):
            display[column] = display[column].dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(lambda value: "" if pd.isna(value) else f"{value:.6f}")
    display = display.astype(object).where(pd.notna(display), "")
    lines = ["| " + " | ".join(display.columns) + " |", "| " + " | ".join(["---"] * len(display.columns)) + " |"]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in display.values.tolist())
    return "\n".join(lines)


def build_summary(labels: pd.DataFrame, config: dict, liquidity_source: str, warnings: list[str]) -> pd.DataFrame:
    total = len(labels)
    metrics = [
        ("market", config["tradability"]["market"]),
        ("start_time", config["tradability"]["start_time"]),
        ("end_time", config["tradability"]["end_time"]),
        ("provider_uri", config["qlib"]["provider_uri"]),
        ("rows", total),
        ("instruments", labels["instrument"].nunique() if total else 0),
        ("dates", labels["datetime"].nunique() if total else 0),
        ("can_buy_rate", labels["can_buy"].mean() if total else pd.NA),
        ("can_sell_rate", labels["can_sell"].mean() if total else pd.NA),
        ("avg_tradability_score", labels["tradability_score"].mean() if total else pd.NA),
        ("liquidity_source", liquidity_source),
        ("warning_count", len(warnings)),
    ]
    for column in [
        "is_suspended",
        "is_limit_up",
        "is_limit_down",
        "is_one_price_limit_up",
        "is_one_price_limit_down",
        "is_low_liquidity",
        "is_new_listing",
        "has_price_anomaly",
        "has_volume_anomaly",
        "has_core_missing",
    ]:
        metrics.append((f"{column}_rate", labels[column].mean() if total else pd.NA))
        metrics.append((f"{column}_count", int(labels[column].sum()) if total else 0))
    return pd.DataFrame(metrics, columns=["metric", "value"])


def build_reason_counts(labels: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for reasons in labels["disabled_reason"].fillna(""):
        for reason in str(reasons).split("|"):
            if reason:
                rows.append(reason)
    if not rows:
        return pd.DataFrame(columns=["reason", "count"])
    return (
        pd.Series(rows)
        .value_counts()
        .rename_axis("reason")
        .reset_index(name="count")
        .sort_values(["count", "reason"], ascending=[False, True])
    )


def build_instrument_scores(labels: pd.DataFrame) -> pd.DataFrame:
    return (
        labels.groupby("instrument")
        .agg(
            row_count=("instrument", "size"),
            can_buy_rate=("can_buy", "mean"),
            can_sell_rate=("can_sell", "mean"),
            avg_tradability_score=("tradability_score", "mean"),
            suspended_rate=("is_suspended", "mean"),
            low_liquidity_rate=("is_low_liquidity", "mean"),
            core_missing_rate=("has_core_missing", "mean"),
        )
        .reset_index()
        .sort_values("avg_tradability_score", ascending=False)
    )


def build_date_coverage(labels: pd.DataFrame) -> pd.DataFrame:
    return (
        labels.groupby("datetime")
        .agg(
            instrument_count=("instrument", "size"),
            can_buy_count=("can_buy", "sum"),
            can_sell_count=("can_sell", "sum"),
            can_buy_rate=("can_buy", "mean"),
            can_sell_rate=("can_sell", "mean"),
            avg_tradability_score=("tradability_score", "mean"),
            suspended_count=("is_suspended", "sum"),
            limit_up_count=("is_limit_up", "sum"),
            limit_down_count=("is_limit_down", "sum"),
            low_liquidity_count=("is_low_liquidity", "sum"),
            core_missing_count=("has_core_missing", "sum"),
        )
        .reset_index()
        .sort_values("datetime")
    )


def build_markdown_report(
    summary: pd.DataFrame,
    reason_counts: pd.DataFrame,
    instrument_scores: pd.DataFrame,
    date_coverage: pd.DataFrame,
    config: dict,
    warnings: list[str],
) -> str:
    metric = dict(summary.values.tolist())
    lines = [
        "# A-share Tradability Label Report",
        "",
        "## Scope",
        "",
        f"- Provider URI: `{config['qlib']['provider_uri']}`",
        f"- Market: `{config['tradability']['market']}`",
        f"- Date range: `{config['tradability']['start_time']}` to `{config['tradability']['end_time']}`",
        f"- Data quality directory: `{config['tradability']['data_quality_dir']}`",
        f"- Liquidity source used: `{metric.get('liquidity_source', 'unknown')}`",
        "",
        "## Overall Tradability",
        "",
        markdown_table(summary),
        "",
        "## Disabled Reasons",
        "",
        markdown_table(reason_counts.head(20)),
        "",
        "## Date Coverage",
        "",
        markdown_table(date_coverage.head(10)),
        "",
        "## Lowest Instrument Scores",
        "",
        markdown_table(instrument_scores.sort_values("avg_tradability_score").head(20)),
        "",
        "## Impact Notes",
        "",
        f"- Suspensions: `{metric.get('is_suspended_count', 0)}` rows.",
        f"- Limit up/down: `{metric.get('is_limit_up_count', 0)}` limit-up rows, `{metric.get('is_limit_down_count', 0)}` limit-down rows.",
        f"- One-price limits: `{metric.get('is_one_price_limit_up_count', 0)}` one-price limit-up rows, `{metric.get('is_one_price_limit_down_count', 0)}` one-price limit-down rows.",
        f"- Low liquidity: `{metric.get('is_low_liquidity_count', 0)}` rows.",
        f"- New listing filter: `{metric.get('is_new_listing_count', 0)}` rows.",
        f"- Data quality impact: price anomalies `{metric.get('has_price_anomaly_count', 0)}`, volume anomalies `{metric.get('has_volume_anomaly_count', 0)}`, core missing `{metric.get('has_core_missing_count', 0)}`.",
        "",
        "## Warnings",
        "",
        markdown_table(pd.DataFrame({"warning": warnings})) if warnings else "No warnings.",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(output_dir: Path, labels: pd.DataFrame, config: dict, liquidity_source: str, warnings: list[str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = build_summary(labels, config, liquidity_source, warnings)
    reason_counts = build_reason_counts(labels)
    instrument_scores = build_instrument_scores(labels)
    date_coverage = build_date_coverage(labels)

    labels.to_csv(output_dir / "tradability_labels.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(output_dir / "summary.csv", index=False, encoding="utf-8-sig")
    instrument_scores.to_csv(output_dir / "instrument_scores.csv", index=False, encoding="utf-8-sig")
    date_coverage.to_csv(output_dir / "date_coverage.csv", index=False, encoding="utf-8-sig")
    reason_counts.to_csv(output_dir / "reason_counts.csv", index=False, encoding="utf-8-sig")
    report = build_markdown_report(summary, reason_counts, instrument_scores, date_coverage, config, warnings)
    (output_dir / "tradability_report.md").write_text(report, encoding="utf-8")
