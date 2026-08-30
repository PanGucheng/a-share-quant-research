from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def parse_qlib_intervals(path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        rows.append(
            {
                "instrument": parts[0].upper(),
                "start_date": pd.Timestamp(parts[1]),
                "end_date": pd.Timestamp(parts[2]),
            }
        )
    return pd.DataFrame(rows)


def normalize_market_frame(
    frame: pd.DataFrame,
    *,
    source: str,
    instrument_column: str,
    date_column: str,
    close_column: str,
    volume_column: str,
    amount_column: str,
    instrument_prefix: str | None = None,
    amount_multiplier: float = 1.0,
    volume_multiplier: float = 1.0,
) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            columns=["instrument", "date", "close", "volume", "amount", "source"]
        )
    result = pd.DataFrame(
        {
            "instrument": frame[instrument_column].astype(str).str.upper(),
            "date": pd.to_datetime(frame[date_column], errors="coerce"),
            "close": pd.to_numeric(frame[close_column], errors="coerce"),
            "volume": pd.to_numeric(frame[volume_column], errors="coerce")
            * volume_multiplier,
            "amount": pd.to_numeric(frame[amount_column], errors="coerce")
            * amount_multiplier,
            "source": source,
        }
    )
    result["instrument"] = result["instrument"].map(
        lambda value: (
            f"{value.rsplit('.', 1)[1]}{value.rsplit('.', 1)[0]}"
            if "." in value and value.rsplit(".", 1)[1] in {"SH", "SZ", "BJ"}
            else value
        )
    )
    if instrument_prefix:
        result["instrument"] = instrument_prefix + result["instrument"].str[-6:]
    result = result.dropna(subset=["instrument", "date"]).drop_duplicates(
        ["instrument", "date"]
    )
    return result.sort_values(["instrument", "date"]).reset_index(drop=True)


def compare_market_sources(
    frames: Iterable[pd.DataFrame], *, tolerance: float = 1e-4
) -> tuple[pd.DataFrame, pd.DataFrame]:
    grouped: dict[tuple[str, tuple[str, ...]], list[pd.DataFrame]] = {}
    for frame in frames:
        if not frame.empty:
            source = str(frame["source"].iloc[0])
            family = source.split(":", 1)[0]
            instruments = tuple(sorted(frame["instrument"].astype(str).unique()))
            grouped.setdefault((family, instruments), []).append(frame)
    usable = [pd.concat(parts, ignore_index=True).drop_duplicates(["instrument", "date"]) for parts in grouped.values()]
    if len(usable) < 2:
        return pd.DataFrame(), pd.DataFrame()
    summaries: list[dict[str, Any]] = []
    differences: list[pd.DataFrame] = []
    for index, left in enumerate(usable):
        for right in usable[index + 1 :]:
            if set(left["instrument"].unique()).isdisjoint(right["instrument"].unique()):
                continue
            if str(left["source"].iloc[0]).split(":", 1)[0] == str(right["source"].iloc[0]).split(":", 1)[0]:
                continue
            left_name = str(left["source"].iloc[0])
            right_name = str(right["source"].iloc[0])
            merged = left.merge(
                right,
                on=["instrument", "date"],
                how="outer",
                suffixes=("_left", "_right"),
                indicator=True,
            )
            both = merged.loc[merged["_merge"].eq("both")].copy()
            metrics: dict[str, Any] = {
                "left_source": left_name,
                "right_source": right_name,
                "left_rows": len(left),
                "right_rows": len(right),
                "aligned_rows": len(both),
                "left_only_rows": int(merged["_merge"].eq("left_only").sum()),
                "right_only_rows": int(merged["_merge"].eq("right_only").sum()),
            }
            for column in ("close", "volume", "amount"):
                a = pd.to_numeric(both[f"{column}_left"], errors="coerce")
                b = pd.to_numeric(both[f"{column}_right"], errors="coerce")
                relative = (a - b).abs() / np.maximum(b.abs(), 1.0)
                finite = relative.replace([np.inf, -np.inf], np.nan).dropna()
                metrics[f"{column}_match_rate"] = (
                    float(finite.le(tolerance).mean()) if len(finite) else np.nan
                )
                metrics[f"{column}_median_relative_difference"] = (
                    float(finite.median()) if len(finite) else np.nan
                )
                metrics[f"{column}_maximum_relative_difference"] = (
                    float(finite.max()) if len(finite) else np.nan
                )
            summaries.append(metrics)
            if not both.empty:
                both["close_relative_difference"] = (
                    pd.to_numeric(both["close_left"], errors="coerce")
                    - pd.to_numeric(both["close_right"], errors="coerce")
                ).abs() / np.maximum(
                    pd.to_numeric(both["close_right"], errors="coerce").abs(), 1.0
                )
                differences.append(
                    both.loc[
                        both["close_relative_difference"].gt(tolerance),
                        [
                            "instrument",
                            "date",
                            "close_left",
                            "close_right",
                            "close_relative_difference",
                        ],
                    ]
                    .assign(left_source=left_name, right_source=right_name)
                    .head(100)
                )
    return pd.DataFrame(summaries), (
        pd.concat(differences, ignore_index=True) if differences else pd.DataFrame()
    )


def classify_frontier(
    *,
    technical_start: str,
    stable_start: str,
    semantic_start: str,
    research_grade_start: str,
    evidence: str,
) -> dict[str, str]:
    return {
        "technical_start": technical_start,
        "stable_start": stable_start,
        "semantic_reliability_start": semantic_start,
        "research_grade_frontier": research_grade_start,
        "evidence": evidence,
    }


def audit_statement_revisions(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "rows": 0,
            "instruments": 0,
            "earliest_report_end": "",
            "earliest_available_date": "",
            "update_flag_one_rows": 0,
            "duplicate_report_keys": 0,
            "availability_before_report_end": 0,
        }
    source = frame.copy()
    for column in ("end_date", "ann_date", "f_ann_date"):
        if column in source:
            source[column] = pd.to_datetime(source[column], errors="coerce")
    key = [column for column in ("ts_code", "end_date", "report_type") if column in source]
    duplicates = int(source.duplicated(key, keep=False).sum()) if key else 0
    available = source.get("f_ann_date", source.get("ann_date", pd.Series(dtype="datetime64[ns]")))
    report_end = source.get("end_date", pd.Series(dtype="datetime64[ns]"))
    return {
        "rows": len(source),
        "instruments": int(source["ts_code"].nunique()) if "ts_code" in source else 0,
        "earliest_report_end": report_end.min().date().isoformat() if report_end.notna().any() else "",
        "earliest_available_date": available.min().date().isoformat() if available.notna().any() else "",
        "update_flag_one_rows": int(source.get("update_flag", pd.Series(dtype=object)).astype(str).eq("1").sum()),
        "duplicate_report_keys": duplicates,
        "availability_before_report_end": int((available < report_end).fillna(False).sum()),
    }
