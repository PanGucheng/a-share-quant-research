from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd


def canonical_instrument(value: Any) -> str:
    """Return Qlib's exchange-first instrument spelling (e.g. ``SH600000``)."""

    text = str(value).strip().upper()
    if "." in text:
        code, exchange = text.split(".", 1)
        return f"{exchange}{code}"
    if text[:2] in {"SH", "SZ", "BJ"}:
        return text
    return text


def resolve_lifecycle_evidence(
    stock_basic: pd.DataFrame,
    qlib_intervals: pd.DataFrame,
    market_presence: pd.DataFrame | None = None,
    namechange: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reconcile lifecycle candidates without treating a current snapshot as vintage truth.

    The output deliberately separates *candidate interval evidence* from the global
    historical-vintage qualification.  Qlib intervals and Tushare listing metadata
    can support a reproducible candidate universe, while dated market observations
    provide a useful cross-check; neither proves that the provider knew the state at
    every historical date.
    """

    basic = stock_basic.copy()
    if basic.empty:
        return pd.DataFrame(), pd.DataFrame()
    for column in ("list_date", "delist_date"):
        if column in basic:
            basic[column] = pd.to_datetime(basic[column], format="%Y%m%d", errors="coerce")
    basic["instrument"] = basic["ts_code"].map(canonical_instrument)
    basic["snapshot_status"] = basic.get("list_status", "").astype(str)

    intervals = qlib_intervals.copy()
    if intervals.empty:
        intervals = pd.DataFrame(columns=["instrument", "start_date", "end_date"])
    intervals["instrument"] = intervals.get("instrument", pd.Series(dtype=object)).map(canonical_instrument)
    intervals["start_date"] = pd.to_datetime(intervals.get("start_date"), errors="coerce")
    intervals["end_date"] = pd.to_datetime(intervals.get("end_date"), errors="coerce")
    intervals = intervals.drop_duplicates("instrument")

    presence = market_presence.copy() if market_presence is not None else pd.DataFrame()
    if not presence.empty:
        presence["instrument"] = presence["instrument"].map(canonical_instrument)
        presence["date"] = pd.to_datetime(presence["date"], errors="coerce")
        presence_summary = presence.groupby("instrument", as_index=False).agg(
            observed_first_date=("date", "min"), observed_last_date=("date", "max"),
            observed_source_count=("source", "nunique"), observed_rows=("date", "size"),
        )
    else:
        presence_summary = pd.DataFrame(columns=["instrument", "observed_first_date", "observed_last_date", "observed_source_count", "observed_rows"])

    result = basic.merge(intervals[["instrument", "start_date", "end_date"]], on="instrument", how="outer", suffixes=("", "_qlib"))
    result = result.merge(presence_summary, on="instrument", how="left")
    result["qlib_interval_present"] = result["start_date"].notna() & result["end_date"].notna()
    result["listing_start_match_days"] = (result["start_date"] - result["list_date"]).dt.days.abs()
    result["delisting_end_match_days"] = (result["end_date"] - result["delist_date"]).dt.days.abs()
    result["has_dated_market_crosscheck"] = pd.to_numeric(result["observed_rows"], errors="coerce").fillna(0).gt(0)
    result["candidate_interval_consistent"] = (
        result["qlib_interval_present"]
        & result["list_date"].notna()
        & result["start_date"].ge(result["list_date"] - pd.Timedelta(days=7))
        & (result["delist_date"].isna() | result["end_date"].le(result["delist_date"] + pd.Timedelta(days=7)))
    )
    result["authority_status"] = np.select(
        [result["candidate_interval_consistent"] & result["has_dated_market_crosscheck"], result["candidate_interval_consistent"]],
        ["candidate_cross_checked", "candidate_interval_only"],
        default="unresolved",
    )

    changes = namechange.copy() if namechange is not None else pd.DataFrame()
    if not changes.empty:
        changes["instrument"] = changes["ts_code"].map(canonical_instrument)
        changes["start_date"] = pd.to_datetime(changes.get("start_date"), format="%Y%m%d", errors="coerce")
        changes["end_date"] = pd.to_datetime(changes.get("end_date"), format="%Y%m%d", errors="coerce")
        rename_summary = changes.groupby("instrument", as_index=False).agg(
            rename_event_count=("instrument", "size"), rename_first_date=("start_date", "min"), rename_last_date=("end_date", "max")
        )
    else:
        rename_summary = pd.DataFrame(columns=["instrument", "rename_event_count", "rename_first_date", "rename_last_date"])
    result = result.merge(rename_summary, on="instrument", how="left")
    result["rename_event_count"] = pd.to_numeric(result["rename_event_count"], errors="coerce").fillna(0).astype(int)

    summary = pd.DataFrame([
        {"metric": "security_count", "value": int(len(result))},
        {"metric": "candidate_cross_checked_count", "value": int(result["authority_status"].eq("candidate_cross_checked").sum())},
        {"metric": "candidate_interval_only_count", "value": int(result["authority_status"].eq("candidate_interval_only").sum())},
        {"metric": "unresolved_count", "value": int(result["authority_status"].eq("unresolved").sum())},
        {"metric": "rename_evidence_instrument_count", "value": int(result["rename_event_count"].gt(0).sum())},
        {"metric": "historical_vintage_proven", "value": False},
        {"metric": "survivorship_control_status", "value": "blocked_current_snapshot_not_vintage"},
    ])
    return result, summary


def assess_statement_completeness(
    retrievals: pd.DataFrame,
    *,
    key_columns: Iterable[str] = ("ts_code", "end_date", "report_type", "ann_date", "update_flag"),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Assess whether segmented retrievals exhaust the rows returned by an API.

    A proof is only granted when every segment terminates below its cap, the union
    has no unresolved boundary overlap, and pagination reaches an empty page.  This
    is retrieval completeness—not proof that a provider preserved every historical
    vintage that once existed.
    """

    if retrievals.empty:
        return pd.DataFrame(), pd.DataFrame()
    frame = retrievals.copy()
    required = {"api", "ts_code", "retrieval_mode", "segment_id", "rows", "row_cap_reached", "page_terminal"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"missing retrieval columns: {sorted(missing)}")
    frame["rows"] = pd.to_numeric(frame["rows"], errors="coerce").fillna(0).astype(int)
    frame["row_cap_reached"] = frame["row_cap_reached"].astype(bool)
    frame["page_terminal"] = frame["page_terminal"].astype(bool)
    # A page of exactly ``limit`` rows is not itself a failure when a following
    # offset page terminates.  Collapse pages into logical segments first and only
    # flag a cap when the segment never reaches a terminal page.
    frame["segment_root"] = frame["segment_id"].astype(str).str.rsplit("_", n=1).str[0]
    segment_state = frame.groupby(["api", "ts_code", "retrieval_mode", "segment_root"], as_index=False).agg(
        segment_rows=("rows", "sum"), segment_max_page_rows=("rows", "max"),
        segment_terminal=("page_terminal", "any"), segment_pages=("segment_id", "size"),
    )
    segment_state["unresolved_cap"] = (~segment_state["segment_terminal"]) & segment_state["segment_max_page_rows"].ge(100)
    grouped = segment_state.groupby(["api", "ts_code"], as_index=False).agg(
        retrieval_requests=("segment_pages", "sum"),
        total_rows=("segment_rows", "sum"),
        max_segment_rows=("segment_rows", "max"),
        cap_segments=("unresolved_cap", "sum"),
        terminal_pages=("segment_terminal", "sum"),
        segment_count=("segment_root", "nunique"),
    )
    grouped["all_segments_below_cap"] = grouped["cap_segments"].eq(0)
    grouped["pagination_terminated"] = grouped["terminal_pages"].ge(1)
    grouped["segmented_retrieval_complete"] = grouped["all_segments_below_cap"] & grouped["pagination_terminated"]
    grouped["provider_vintage_complete"] = False
    grouped["completeness_status"] = np.where(grouped["segmented_retrieval_complete"], "retrieval_complete_provider_vintage_unproven", "blocked_retrieval_incomplete")
    summary = grouped.groupby("api", as_index=False).agg(
        issuer_count=("ts_code", "nunique"), complete_issuer_count=("segmented_retrieval_complete", "sum"),
        cap_issuer_count=("cap_segments", lambda values: int((values > 0).sum())),
        retrieval_complete_rate=("segmented_retrieval_complete", "mean"),
    )
    summary["provider_vintage_complete"] = False
    summary["authority_status"] = np.where(summary["retrieval_complete_rate"].eq(1.0), "retrieval_complete_provider_vintage_unproven", "blocked_retrieval_incomplete")
    return grouped, summary


def authority_frontier(
    coverage: pd.DataFrame,
    lifecycle: pd.DataFrame,
    statement_summary: pd.DataFrame,
    *,
    layer: str,
    minimum_coverage: float = 0.90,
    consecutive_periods: int = 4,
) -> dict[str, Any]:
    """Recompute a candidate frontier with an explicit authority gate."""

    subset = coverage.loc[coverage["layer"].eq(layer)].sort_values("trade_date").reset_index(drop=True)
    if subset.empty:
        return {"layer": layer, "candidate_frontier": "", "authoritative": False, "reason": "no_coverage"}
    passed = subset["coverage_ratio"].ge(minimum_coverage).fillna(False).to_numpy()
    start = int(np.flatnonzero(~passed)[-1] + 1) if (~passed).any() else 0
    candidate = str(subset.loc[len(subset) - (len(passed) - start), "trade_date"]) if len(passed) - start >= consecutive_periods else ""
    lifecycle_ok = bool(not lifecycle.empty and lifecycle.get("historical_vintage_proven", pd.Series([False])).astype(bool).all())
    statement_ok = bool(not statement_summary.empty and statement_summary["provider_vintage_complete"].astype(bool).all())
    return {
        "layer": layer,
        "candidate_frontier": candidate,
        "authoritative": bool(candidate and lifecycle_ok and statement_ok),
        "reason": "lifecycle_vintage_and_statement_vintage_required",
        "lifecycle_vintage_proven": lifecycle_ok,
        "statement_provider_vintage_complete": statement_ok,
    }
