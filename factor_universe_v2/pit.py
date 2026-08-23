from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

import pandas as pd


PIT_DATE_PRECEDENCE = {
    "income": ("f_ann_date", "ann_date"),
    "balancesheet": ("f_ann_date", "ann_date"),
    "cashflow": ("f_ann_date", "ann_date"),
    "fina_indicator": ("ann_date",),
    "forecast": ("ann_date",),
    "express": ("ann_date",),
    "dividend": ("ann_date",),
}


def _row_fingerprint(row: pd.Series, columns: list[str]) -> str:
    payload = {column: None if pd.isna(row[column]) else str(row[column]) for column in columns}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def prepare_pit_records(
    frame: pd.DataFrame,
    *,
    dataset: str,
    entity_keys: Iterable[str] = ("ts_code",),
    report_period_column: str = "end_date",
) -> pd.DataFrame:
    """Attach fail-closed availability and deterministic revision order to source rows.

    The report period is never used as an availability fallback. Rows without a proven
    announcement date remain research-pending and cannot be selected by ``asof_pit_records``.
    """
    if dataset not in PIT_DATE_PRECEDENCE:
        raise ValueError(f"unsupported PIT dataset: {dataset}")
    entity = list(entity_keys)
    required = set(entity + [report_period_column])
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{dataset} frame missing PIT columns: {missing}")
    result = frame.copy()
    available = pd.Series(pd.NaT, index=result.index, dtype="datetime64[ns]")
    source = pd.Series(pd.NA, index=result.index, dtype="string")
    for column in PIT_DATE_PRECEDENCE[dataset]:
        if column not in result:
            continue
        parsed = pd.to_datetime(result[column], format="%Y%m%d", errors="coerce")
        choose = available.isna() & parsed.notna()
        available.loc[choose] = parsed.loc[choose]
        source.loc[choose] = column
    result["information_available_date"] = available
    result["availability_source"] = source
    result["pit_status"] = available.notna().map({True: "authoritative", False: "research_pending"})
    report_period = pd.to_datetime(result[report_period_column], format="%Y%m%d", errors="coerce")
    if dataset in {"income", "balancesheet", "cashflow", "fina_indicator"}:
        invalid = available.notna() & report_period.notna() & available.lt(report_period)
        if invalid.any():
            raise ValueError(f"{dataset} contains announcement dates before report periods")
    fingerprint_columns = sorted(str(column) for column in result.columns if column != "source_row_hash")
    result["source_row_hash"] = result.apply(
        lambda row: _row_fingerprint(row, fingerprint_columns), axis=1
    )
    revision_keys = entity + [report_period_column]
    for optional in ("report_type", "comp_type"):
        if optional in result:
            revision_keys.append(optional)
    result = result.sort_values(
        revision_keys + ["information_available_date", "source_row_hash"],
        na_position="last",
    ).reset_index(drop=True)
    result["revision_sequence"] = result.groupby(revision_keys, dropna=False).cumcount() + 1
    return result


def asof_pit_records(
    prepared: pd.DataFrame,
    *,
    as_of_date: str | pd.Timestamp,
    entity_keys: Iterable[str] = ("ts_code",),
    report_period_column: str = "end_date",
) -> pd.DataFrame:
    """Return the latest disclosed revision available on or before ``as_of_date``."""
    required = {"information_available_date", "revision_sequence", report_period_column, *entity_keys}
    missing = sorted(required - set(prepared.columns))
    if missing:
        raise ValueError(f"prepared PIT frame missing columns: {missing}")
    cutoff = pd.Timestamp(as_of_date).normalize()
    eligible = prepared.loc[
        prepared["information_available_date"].notna()
        & prepared["information_available_date"].le(cutoff)
    ].copy()
    keys = list(entity_keys) + [report_period_column]
    for optional in ("report_type", "comp_type"):
        if optional in eligible:
            keys.append(optional)
    if eligible.empty:
        return eligible
    eligible = eligible.sort_values(
        keys + ["information_available_date", "revision_sequence", "source_row_hash"]
    )
    return eligible.groupby(keys, dropna=False, as_index=False).tail(1).reset_index(drop=True)
