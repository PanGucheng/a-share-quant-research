from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


KEYS = ["datetime", "instrument"]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def practical_market_coverage(
    expected_presence: pd.DataFrame,
    observed: pd.DataFrame,
    *,
    layer: str,
) -> pd.DataFrame:
    """Measure provider coverage against dated tradable presence, not a current snapshot.

    ``expected_presence`` is the actual Qlib price/volume presence after lifecycle
    filtering. Suspended securities with no market row do not inflate the denominator.
    """
    expected = expected_presence[KEYS].drop_duplicates()
    actual = observed[KEYS].drop_duplicates()
    if expected.duplicated(KEYS).any() or actual.duplicated(KEYS).any():
        raise ValueError("coverage inputs contain duplicate keys")
    dates = sorted(set(expected["datetime"]) | set(actual["datetime"]))
    rows: list[dict[str, Any]] = []
    for date in dates:
        expected_set = set(expected.loc[expected["datetime"].eq(date), "instrument"])
        observed_set = set(actual.loc[actual["datetime"].eq(date), "instrument"])
        aligned = expected_set & observed_set
        rows.append(
            {
                "datetime": pd.Timestamp(date),
                "layer": layer,
                "expected_presence_count": len(expected_set),
                "observed_count": len(observed_set),
                "aligned_count": len(aligned),
                "missing_count": len(expected_set - observed_set),
                "unexpected_count": len(observed_set - expected_set),
                "coverage_ratio": len(aligned) / len(expected_set) if expected_set else np.nan,
            }
        )
    return pd.DataFrame(rows)


def earliest_stable_frontier(
    coverage: pd.DataFrame,
    *,
    minimum_coverage: float,
    minimum_tail_fraction: float,
    minimum_dates: int,
) -> dict[str, Any]:
    """Return the earliest date whose remaining history is sufficiently complete."""
    ordered = coverage.sort_values("datetime").reset_index(drop=True)
    passing = ordered["coverage_ratio"].ge(minimum_coverage).to_numpy()
    for position, row in ordered.iterrows():
        tail = passing[position:]
        if len(tail) >= minimum_dates and float(tail.mean()) >= minimum_tail_fraction:
            return {
                "frontier": pd.Timestamp(row["datetime"]),
                "tail_date_count": len(tail),
                "tail_passing_fraction": float(tail.mean()),
                "minimum_tail_coverage": float(
                    ordered.loc[position:, "coverage_ratio"].min()
                ),
                "admitted": True,
            }
    return {
        "frontier": pd.NaT,
        "tail_date_count": 0,
        "tail_passing_fraction": 0.0,
        "minimum_tail_coverage": np.nan,
        "admitted": False,
    }


def audit_practical_pit(
    aligned: pd.DataFrame,
    events: pd.DataFrame,
) -> pd.DataFrame:
    availability = pd.to_datetime(aligned["information_available_date"], errors="coerce")
    decisions = pd.to_datetime(aligned["datetime"], errors="raise")
    visible = availability.notna()
    future = visible & availability.gt(decisions)
    event_dates = pd.to_datetime(events["information_available_date"], errors="coerce")
    missing_event_availability = int(event_dates.isna().sum())
    report_periods = pd.to_datetime(events["report_period"], errors="coerce")
    reversed_periods = int(report_periods.gt(event_dates).sum())
    duplicate_events = int(
        events.duplicated(["instrument", "information_available_date"], keep=False).sum()
    )
    selected_dates = aligned.loc[visible, ["instrument", "datetime", "information_available_date"]]
    monotone_violations = 0
    for _, group in selected_dates.sort_values(["instrument", "datetime"]).groupby(
        "instrument", sort=False
    ):
        monotone_violations += int(
            pd.to_datetime(group["information_available_date"]).diff().dt.days.lt(0).sum()
        )

    # Independently reconstruct the latest admissible event date.  This catches
    # accidental forward joins and stale/incorrect forward-fill even when every
    # selected date happens to be earlier than its decision date.
    latest_mismatches = 0
    for instrument, key_group in aligned.groupby("instrument", sort=False):
        left = key_group[["datetime", "information_available_date"]].copy()
        left["datetime"] = pd.to_datetime(left["datetime"], errors="raise")
        left = left.sort_values("datetime")
        right = events.loc[
            events["instrument"].eq(instrument), ["information_available_date"]
        ].copy()
        right["expected_information_available_date"] = pd.to_datetime(
            right["information_available_date"], errors="coerce"
        )
        right = right.drop(columns="information_available_date").dropna().sort_values(
            "expected_information_available_date"
        )
        expected = pd.merge_asof(
            left[["datetime"]],
            right,
            left_on="datetime",
            right_on="expected_information_available_date",
            direction="backward",
            allow_exact_matches=True,
        )["expected_information_available_date"]
        actual = pd.to_datetime(
            left["information_available_date"], errors="coerce"
        ).reset_index(drop=True)
        latest_mismatches += int(
            actual.fillna(pd.Timestamp.min)
            .ne(expected.reset_index(drop=True).fillna(pd.Timestamp.min))
            .sum()
        )
    rows = [
        ("no_future_statement_access", int(future.sum()) == 0, int(future.sum()), 0),
        (
            "event_availability_present",
            missing_event_availability == 0,
            missing_event_availability,
            0,
        ),
        (
            "report_period_not_used_as_availability",
            reversed_periods == 0,
            reversed_periods,
            0,
        ),
        (
            "one_effective_event_per_issuer_day",
            duplicate_events == 0,
            duplicate_events,
            0,
        ),
        (
            "selected_event_is_latest_public_event",
            latest_mismatches == 0,
            latest_mismatches,
            0,
        ),
        (
            "selected_availability_is_monotone",
            monotone_violations == 0,
            monotone_violations,
            0,
        ),
    ]
    return pd.DataFrame(
        [
            {
                "check": check,
                "status": "pass" if passed else "fail",
                "observed": observed,
                "required": required,
            }
            for check, passed, observed, required in rows
        ]
    )


def compare_matrix_overlap(
    extended: pd.DataFrame,
    frozen: pd.DataFrame,
    factors: Iterable[str],
    *,
    absolute_tolerance: float = 1e-10,
    relative_tolerance: float = 1e-8,
) -> pd.DataFrame:
    names = list(factors)
    left = extended[KEYS + names].copy()
    right = frozen[KEYS + names].copy()
    joined = left.merge(right, on=KEYS, how="outer", suffixes=("_extended", "_frozen"), indicator=True)
    rows: list[dict[str, Any]] = []
    common = joined["_merge"].eq("both")
    for factor in names:
        a = pd.to_numeric(joined.loc[common, f"{factor}_extended"], errors="coerce").to_numpy()
        b = pd.to_numeric(joined.loc[common, f"{factor}_frozen"], errors="coerce").to_numpy()
        both_nan = np.isnan(a) & np.isnan(b)
        finite = np.isfinite(a) & np.isfinite(b)
        close = np.zeros(len(a), dtype=bool)
        close[both_nan] = True
        close[finite] = np.isclose(
            a[finite], b[finite], atol=absolute_tolerance, rtol=relative_tolerance
        )
        rows.append(
            {
                "factor": factor,
                "extended_key_count": len(left),
                "frozen_key_count": len(right),
                "common_key_count": int(common.sum()),
                "extended_only_key_count": int(joined["_merge"].eq("left_only").sum()),
                "frozen_only_key_count": int(joined["_merge"].eq("right_only").sum()),
                "value_match_count": int(close.sum()),
                "value_difference_count": int((~close).sum()),
                "value_match_ratio": float(close.mean()) if len(close) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def partition_identity(rows: pd.DataFrame) -> str:
    required = {"partition_id", "output_sha256", "row_count", "factor_count"}
    missing = sorted(required - set(rows.columns))
    if missing:
        raise ValueError(f"partition identity missing columns: {missing}")
    identity_columns = [
        column
        for column in ("year", "layer", "partition_id", "output_sha256", "row_count", "factor_count")
        if column in rows
    ]
    sort_columns = [column for column in ("year", "layer", "partition_id") if column in rows]
    payload = rows[identity_columns].sort_values(sort_columns).to_dict("records")
    return "extended-matrix:" + canonical_hash(payload)
