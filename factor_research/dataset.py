from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from factor_research.diagnostics import attach_tradability, load_tradability_labels
from factor_research.registry import FactorSpec


@dataclass(frozen=True)
class TradableFilterConfig:
    min_liquidity_bucket: int = 3
    min_tradability_score: float = 75.0
    exclude_quality_statuses: tuple[str, ...] = ("severe",)
    require_can_buy: bool = True


FACTOR_DATA_COLUMNS = [
    "datetime",
    "instrument",
    "factor",
    "factor_value",
    "factor_quantile",
    "label",
    "forward_return",
    "can_buy",
    "can_sell",
    "liquidity_bucket",
    "tradability_score",
    "data_quality_status",
    "has_data_quality_issue",
]


def load_data_quality_flags(path: Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame()
    row_issues = path / "row_issues.csv"
    if not row_issues.exists():
        return pd.DataFrame()
    issues = pd.read_csv(row_issues, usecols=["datetime", "instrument", "category", "rule"], parse_dates=["datetime"])
    if issues.empty:
        return pd.DataFrame(columns=["datetime", "instrument", "has_data_quality_issue", "data_quality_issue_count", "data_quality_rules"])
    issues["instrument"] = issues["instrument"].astype(str).str.upper()
    rules = (
        issues.groupby(["datetime", "instrument"])["rule"]
        .apply(lambda values: "|".join(sorted(set(str(value) for value in values if pd.notna(value)))))
        .reset_index(name="data_quality_rules")
    )
    counts = issues.groupby(["datetime", "instrument"]).size().reset_index(name="data_quality_issue_count")
    result = counts.merge(rules, on=["datetime", "instrument"], how="left")
    result["has_data_quality_issue"] = True
    return result


def attach_data_quality_flags(frame: pd.DataFrame, data_quality_dir: Path | None) -> pd.DataFrame:
    result = frame.copy()
    result["instrument"] = result["instrument"].astype(str).str.upper()
    flags = load_data_quality_flags(data_quality_dir)
    if flags.empty:
        result["has_data_quality_issue"] = False
        result["data_quality_issue_count"] = 0
        result["data_quality_rules"] = ""
        return result
    result = result.merge(flags, on=["datetime", "instrument"], how="left")
    result["has_data_quality_issue"] = result["has_data_quality_issue"].where(
        result["has_data_quality_issue"].notna(), False
    ).astype(bool)
    result["data_quality_issue_count"] = pd.to_numeric(result["data_quality_issue_count"], errors="coerce").fillna(0).astype(int)
    result["data_quality_rules"] = result["data_quality_rules"].fillna("")
    return result


def prepare_research_frame(
    frame: pd.DataFrame,
    tradability_dir: Path,
    data_quality_dir: Path | None = None,
) -> pd.DataFrame:
    labels = load_tradability_labels(tradability_dir)
    result = attach_tradability(frame, labels)
    result = attach_data_quality_flags(result, data_quality_dir)
    if "data_quality_status" not in result.columns:
        result["data_quality_status"] = "unknown"
    return result


def apply_tradable_filter(frame: pd.DataFrame, config: TradableFilterConfig) -> pd.DataFrame:
    mask = frame["liquidity_bucket"].ge(config.min_liquidity_bucket) & frame["tradability_score"].ge(
        config.min_tradability_score
    )
    if config.require_can_buy:
        mask &= frame["can_buy"].astype(bool)
    if "data_quality_status" in frame.columns and config.exclude_quality_statuses:
        mask &= ~frame["data_quality_status"].fillna("unknown").isin(config.exclude_quality_statuses)
    if "has_core_missing" in frame.columns:
        mask &= ~frame["has_core_missing"].fillna(False).astype(bool)
    return frame.loc[mask].copy()


def factor_data_schema_markdown() -> str:
    lines = [
        "# Factor Data Schema",
        "",
        "The internal evaluator uses a wide daily cross-sectional frame for speed, but the research contract follows an Alphalens-style long factor_data schema.",
        "",
        "| column | meaning |",
        "| --- | --- |",
    ]
    meanings = {
        "datetime": "Trading date.",
        "instrument": "Qlib instrument code.",
        "factor": "Factor name from the registry.",
        "factor_value": "Numeric factor value before quantile bucketing.",
        "factor_quantile": "Daily cross-sectional quantile, 1 is lowest.",
        "label": "Forward-return label name.",
        "forward_return": "Forward return for the label.",
        "can_buy": "Tradability label from the unified tradability layer.",
        "can_sell": "Tradability label from the unified tradability layer.",
        "liquidity_bucket": "Daily liquidity bucket from the tradability layer.",
        "tradability_score": "Tradability score from the tradability layer.",
        "data_quality_status": "Data quality status carried from tradability/data_quality outputs.",
        "has_data_quality_issue": "Whether row-level data_quality flagged this date/instrument.",
    }
    lines.extend(f"| `{column}` | {meanings[column]} |" for column in FACTOR_DATA_COLUMNS)
    return "\n".join(lines) + "\n"


def to_factor_data(
    frame: pd.DataFrame,
    specs: list[FactorSpec],
    labels: list[str],
    quantiles: int,
) -> pd.DataFrame:
    rows = []
    context_cols = [
        column
        for column in [
            "can_buy",
            "can_sell",
            "liquidity_bucket",
            "tradability_score",
            "data_quality_status",
            "has_data_quality_issue",
        ]
        if column in frame.columns
    ]
    for spec in specs:
        if spec.name not in frame.columns:
            continue
        quantile = frame.groupby("datetime")[spec.name].transform(
            lambda values: pd.qcut(values, quantiles, labels=False, duplicates="drop") + 1
            if values.notna().sum() >= quantiles
            else pd.Series(pd.NA, index=values.index)
        )
        base = frame[["datetime", "instrument", spec.name, *context_cols]].copy()
        base = base.rename(columns={spec.name: "factor_value"})
        base["factor"] = spec.name
        base["factor_quantile"] = quantile
        for label in labels:
            if label not in frame.columns:
                continue
            labelled = base.copy()
            labelled["label"] = label
            labelled["forward_return"] = frame[label]
            rows.append(labelled)
    if not rows:
        return pd.DataFrame(columns=FACTOR_DATA_COLUMNS)
    result = pd.concat(rows, ignore_index=True)
    for column in FACTOR_DATA_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA
    return result[FACTOR_DATA_COLUMNS]
