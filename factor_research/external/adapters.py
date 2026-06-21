from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pandas as pd


@dataclass(frozen=True)
class AdapterReport:
    target: str
    input_rows: int
    output_rows: int
    factor_count: int
    label_count: int
    first_date: str
    last_date: str
    notes: tuple[str, ...] = ()

    def to_markdown(self) -> str:
        rows = [
            f"# {self.target} Adapter Report",
            "",
            "| metric | value |",
            "| --- | --- |",
            f"| input rows | {self.input_rows} |",
            f"| output rows | {self.output_rows} |",
            f"| factor count | {self.factor_count} |",
            f"| label count | {self.label_count} |",
            f"| first date | {self.first_date} |",
            f"| last date | {self.last_date} |",
        ]
        if self.notes:
            rows.extend(["", "## Notes", ""])
            rows.extend(f"- {note}" for note in self.notes)
        return "\n".join(rows) + "\n"


def _normalize_factor_data(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"datetime", "instrument", "factor", "factor_value", "label", "forward_return"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"factor_data is missing required columns: {sorted(missing)}")
    result = frame.copy()
    result["datetime"] = pd.to_datetime(result["datetime"])
    result["instrument"] = result["instrument"].astype(str).str.upper()
    result["factor"] = result["factor"].astype(str)
    result["label"] = result["label"].astype(str)
    result["factor_value"] = pd.to_numeric(result["factor_value"], errors="coerce")
    result["forward_return"] = pd.to_numeric(result["forward_return"], errors="coerce")
    return result


def _label_to_period(label: str, label_period_map: Mapping[str, str] | None = None) -> str:
    if label_period_map and label in label_period_map:
        return label_period_map[label]
    if label.startswith("label_") and "d" in label:
        part = label.removeprefix("label_").split("_", maxsplit=1)[0]
        if part.endswith("d") and part[:-1].isdigit():
            return f"{part[:-1]}D"
    return label


def _base_report(target: str, source: pd.DataFrame, output: pd.DataFrame, notes: tuple[str, ...]) -> AdapterReport:
    dates = pd.to_datetime(source["datetime"]) if not source.empty else pd.Series(dtype="datetime64[ns]")
    return AdapterReport(
        target=target,
        input_rows=int(len(source)),
        output_rows=int(len(output)),
        factor_count=int(source["factor"].nunique()) if "factor" in source else 0,
        label_count=int(source["label"].nunique()) if "label" in source else 0,
        first_date=str(dates.min().date()) if not dates.empty else "",
        last_date=str(dates.max().date()) if not dates.empty else "",
        notes=notes,
    )


def to_alphalens_factor_data(
    factor_data: pd.DataFrame,
    factor_name: str,
    label_period_map: Mapping[str, str] | None = None,
    group_column: str | None = None,
) -> tuple[pd.DataFrame, AdapterReport]:
    """Convert internal long factor data to an Alphalens-compatible frame.

    The returned DataFrame uses a ``(date, asset)`` MultiIndex and contains
    ``factor``, one or more forward return period columns such as ``10D``, and
    optional ``factor_quantile``/``group`` columns. No Alphalens metric is
    computed here.
    """

    source = _normalize_factor_data(factor_data)
    source = source[source["factor"] == factor_name].copy()
    if source.empty:
        empty = pd.DataFrame().rename_axis(index=["date", "asset"])
        report = _base_report("alphalens_reloaded", source, empty, (f"factor `{factor_name}` has no rows",))
        return empty, report

    base_columns = ["datetime", "instrument", "factor_value"]
    if "factor_quantile" in source.columns:
        base_columns.append("factor_quantile")
    if group_column and group_column in source.columns:
        base_columns.append(group_column)
    base = source[base_columns].drop_duplicates(["datetime", "instrument"]).rename(columns={"factor_value": "factor"})

    returns = source.pivot_table(
        index=["datetime", "instrument"],
        columns="label",
        values="forward_return",
        aggfunc="first",
    ).rename(columns=lambda label: _label_to_period(str(label), label_period_map))

    result = base.set_index(["datetime", "instrument"]).join(returns, how="left")
    if group_column and group_column in result.columns:
        result = result.rename(columns={group_column: "group"})
    result.index = result.index.set_names(["date", "asset"])
    result = result.replace([float("inf"), float("-inf")], pd.NA).dropna().sort_index()
    report = _base_report(
        "alphalens_reloaded",
        source,
        result,
        (
            "adapter only converts schema; use alphalens-reloaded performance/tears functions for metrics",
            "tradability and data_quality filters must be applied before this adapter",
        ),
    )
    return result, report


def to_jqfactor_inputs(
    factor_data: pd.DataFrame,
    factor_name: str,
    label_period_map: Mapping[str, str] | None = None,
    group_column: str | None = None,
    weight_column: str | None = None,
) -> tuple[dict[str, pd.DataFrame | pd.Series | None], AdapterReport]:
    """Convert internal long factor data to jqfactor-style aligned objects."""

    source = _normalize_factor_data(factor_data)
    source = source[source["factor"] == factor_name].copy()
    if source.empty:
        report = _base_report("jqfactor_analyzer", source, pd.DataFrame(), (f"factor `{factor_name}` has no rows",))
        return {"factor": pd.Series(dtype=float), "forward_returns": pd.DataFrame(), "groupby": None, "weights": None}, report

    index_cols = ["datetime", "instrument"]
    factor = (
        source[index_cols + ["factor_value"]]
        .drop_duplicates(index_cols)
        .set_index(index_cols)["factor_value"]
        .sort_index()
    )
    factor.index = factor.index.set_names(["date", "asset"])

    forward_returns = source.pivot_table(
        index=index_cols,
        columns="label",
        values="forward_return",
        aggfunc="first",
    ).rename(columns=lambda label: _label_to_period(str(label), label_period_map))
    forward_returns.index = forward_returns.index.set_names(["date", "asset"])
    forward_returns = forward_returns.sort_index()

    groupby = None
    if group_column and group_column in source.columns:
        groupby = (
            source[index_cols + [group_column]]
            .drop_duplicates(index_cols)
            .set_index(index_cols)[group_column]
            .sort_index()
        )
        groupby.index = groupby.index.set_names(["date", "asset"])

    weights = None
    if weight_column and weight_column in source.columns:
        weights = (
            source[index_cols + [weight_column]]
            .drop_duplicates(index_cols)
            .set_index(index_cols)[weight_column]
            .sort_index()
        )
        weights.index = weights.index.set_names(["date", "asset"])

    output = pd.DataFrame({"factor": factor}).join(forward_returns, how="left")
    if "factor_quantile" in source.columns:
        quantile = (
            source[index_cols + ["factor_quantile"]]
            .drop_duplicates(index_cols)
            .set_index(index_cols)["factor_quantile"]
            .sort_index()
        )
        quantile.index = quantile.index.set_names(["date", "asset"])
        output["factor_quantile"] = quantile
    if groupby is not None:
        output["group"] = groupby
    if weights is not None:
        output["weights"] = weights
    else:
        output["weights"] = 1.0
    output = output.replace([float("inf"), float("-inf")], pd.NA).dropna().sort_index()
    output["factor_quantile"] = output["factor_quantile"].astype(int)
    output["weights"] = output.groupby(
        [output.index.get_level_values("date"), "factor_quantile"], observed=True
    )["weights"].transform(lambda values: values / values.sum())

    factor = output["factor"]
    forward_returns = output[[column for column in output.columns if str(column).startswith("period_")]]
    groupby = output["group"] if "group" in output.columns else None
    weights = output["weights"]
    report = _base_report(
        "jqfactor_analyzer",
        source,
        output,
        (
            "adapter produces aligned factor/forward_return/groupby/weights objects",
            "jqfactor_analyzer metrics should be called from its own performance/analyze modules",
        ),
    )
    return {
        "factor": factor,
        "forward_returns": forward_returns,
        "groupby": groupby,
        "weights": weights,
        "factor_data": output,
    }, report


def to_qlib_score_frame(
    factor_data: pd.DataFrame,
    factor_name: str,
    label: str,
) -> tuple[pd.DataFrame, AdapterReport]:
    """Convert internal long factor data to a Qlib-style score/label frame."""

    source = _normalize_factor_data(factor_data)
    source = source[(source["factor"] == factor_name) & (source["label"] == label)].copy()
    if source.empty:
        empty = pd.DataFrame(columns=["datetime", "instrument", "score", "label"])
        report = _base_report("qlib_eval", source, empty, (f"factor `{factor_name}` and label `{label}` have no rows",))
        return empty, report
    result = source[["datetime", "instrument", "factor_value", "forward_return"]].rename(
        columns={"factor_value": "score", "forward_return": "label"}
    )
    result = result.sort_values(["datetime", "instrument"]).reset_index(drop=True)
    report = _base_report(
        "qlib_eval",
        source,
        result,
        ("adapter produces score/label pairs; Qlib risk_analysis and indicator_analysis stay external",),
    )
    return result, report


def write_adapter_report(report: AdapterReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.to_markdown(), encoding="utf-8")
