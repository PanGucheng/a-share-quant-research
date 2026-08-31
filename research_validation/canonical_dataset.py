from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


KEYS = ["datetime", "instrument"]


def dated_membership_axis(
    intervals: pd.DataFrame,
    start: pd.Timestamp | str,
    end: pd.Timestamp | str,
) -> list[str]:
    required = {"instrument", "start_date", "end_date"}
    missing = sorted(required - set(intervals.columns))
    if missing:
        raise ValueError(f"membership intervals missing columns: {missing}")
    left = pd.Timestamp(start)
    right = pd.Timestamp(end)
    starts = pd.to_datetime(intervals["start_date"], errors="raise")
    ends = pd.to_datetime(intervals["end_date"], errors="raise")
    active = starts.le(right) & ends.ge(left)
    return sorted(intervals.loc[active, "instrument"].astype(str).str.upper().unique())


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def canonical_dataset_identity(
    partition_manifest: pd.DataFrame,
    factor_lineage: pd.DataFrame,
) -> str:
    partition_columns = [
        "segment_id",
        "partition_id",
        "effective_start",
        "effective_end",
        "output_sha256",
        "row_count",
        "factor_count",
        "lineage_action",
    ]
    lineage_columns = [
        "factor",
        "authoritative_semantics",
        "historical_action",
        "continuation_action",
        "research_usable",
    ]
    missing_partitions = sorted(set(partition_columns) - set(partition_manifest.columns))
    missing_lineage = sorted(set(lineage_columns) - set(factor_lineage.columns))
    if missing_partitions or missing_lineage:
        raise ValueError(
            "canonical identity inputs missing columns: "
            f"partitions={missing_partitions}, lineage={missing_lineage}"
        )
    payload = {
        "partitions": partition_manifest[partition_columns]
        .sort_values(["segment_id", "partition_id"], kind="stable")
        .to_dict("records"),
        "factor_lineage": factor_lineage[lineage_columns]
        .sort_values("factor", kind="stable")
        .to_dict("records"),
    }
    return "canonical-dataset:" + canonical_hash(payload)


def read_effective_partition(
    row: pd.Series | dict[str, Any],
    *,
    columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    item = dict(row)
    requested = None if columns is None else list(dict.fromkeys([*KEYS, *columns]))
    start = pd.Timestamp(item["effective_start"])
    end = pd.Timestamp(item["effective_end"])
    frame = pd.read_parquet(
        Path(str(item["partition_path"])),
        columns=requested,
        filters=[("datetime", ">=", start), ("datetime", "<=", end)],
    )
    frame["datetime"] = pd.to_datetime(frame["datetime"], errors="raise")
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    return (
        frame.loc[frame["datetime"].between(start, end)]
        .sort_values(KEYS, kind="stable")
        .reset_index(drop=True)
    )


def validate_partition_segments(partition_manifest: pd.DataFrame) -> pd.DataFrame:
    required = {
        "segment_id",
        "partition_id",
        "effective_start",
        "effective_end",
        "partition_path",
        "row_count",
        "factor_count",
    }
    missing = sorted(required - set(partition_manifest.columns))
    if missing:
        raise ValueError(f"canonical partition manifest missing columns: {missing}")
    rows: list[dict[str, Any]] = []
    manifest = partition_manifest.copy()
    manifest["effective_start"] = pd.to_datetime(manifest["effective_start"])
    manifest["effective_end"] = pd.to_datetime(manifest["effective_end"])
    for partition_id, group in manifest.groupby("partition_id", sort=True):
        ordered = group.sort_values(["effective_start", "effective_end"], kind="stable")
        overlap_count = 0
        reversed_count = int(ordered["effective_start"].gt(ordered["effective_end"]).sum())
        previous_end: pd.Timestamp | None = None
        for item in ordered.itertuples(index=False):
            start = pd.Timestamp(item.effective_start)
            end = pd.Timestamp(item.effective_end)
            if previous_end is not None and start <= previous_end:
                overlap_count += 1
            previous_end = max(previous_end, end) if previous_end is not None else end
        rows.append(
            {
                "partition_id": partition_id,
                "segment_count": len(ordered),
                "factor_count_min": int(ordered["factor_count"].min()),
                "factor_count_max": int(ordered["factor_count"].max()),
                "first_effective_date": ordered["effective_start"].min(),
                "last_effective_date": ordered["effective_end"].max(),
                "overlap_count": overlap_count,
                "reversed_interval_count": reversed_count,
                "status": (
                    "pass"
                    if overlap_count == 0
                    and reversed_count == 0
                    and ordered["factor_count"].nunique() == 1
                    else "fail"
                ),
            }
        )
    return pd.DataFrame(rows)


def validate_semantic_continuity(factor_lineage: pd.DataFrame) -> pd.DataFrame:
    required = {
        "factor",
        "authoritative_semantics",
        "historical_semantics",
        "continuation_semantics",
    }
    missing = sorted(required - set(factor_lineage.columns))
    if missing:
        raise ValueError(f"factor lineage missing columns: {missing}")
    result = factor_lineage[
        [
            "factor",
            "authoritative_semantics",
            "historical_semantics",
            "continuation_semantics",
        ]
    ].copy()
    result["historical_matches_authority"] = result["historical_semantics"].eq(
        result["authoritative_semantics"]
    )
    result["continuation_matches_authority"] = result["continuation_semantics"].eq(
        result["authoritative_semantics"]
    )
    result["implementation_regime_break"] = ~(
        result["historical_matches_authority"]
        & result["continuation_matches_authority"]
    )
    result["status"] = result["implementation_regime_break"].map(
        {True: "fail", False: "pass"}
    )
    return result


def summarize_values(series: pd.Series) -> dict[str, int | float]:
    numeric = pd.to_numeric(series, errors="coerce")
    finite_mask = np.isfinite(numeric.to_numpy(dtype=float))
    finite = numeric.loc[finite_mask]
    return {
        "row_count": int(len(numeric)),
        "valid_count": int(finite_mask.sum()),
        "missing_count": int(numeric.isna().sum()),
        "nonfinite_count": int(np.isinf(numeric.to_numpy(dtype=float)).sum()),
        "coverage": float(finite_mask.mean()) if len(numeric) else float("nan"),
        "median": float(finite.median()) if len(finite) else float("nan"),
        "q01": float(finite.quantile(0.01)) if len(finite) else float("nan"),
        "q99": float(finite.quantile(0.99)) if len(finite) else float("nan"),
    }
