from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera import Check


SCREENING_ROLES = frozenset(
    {
        "alpha_candidate",
        "excluded_high_turnover",
        "excluded_redundant",
        "excluded_unstable_context",
        "holdout",
        "monitor",
    }
)
JUDGEMENT_ROLES = frozenset(
    SCREENING_ROLES
    | {
        "new_source_alpha_probe",
        "new_source_data_watch",
        "new_source_mixed_signal",
        "new_source_monitor",
    }
)
PROBE_ROLES = frozenset({"new_source_alpha_probe", "new_source_data_watch", "new_source_mixed_signal"})
LIQUIDITY_BUCKETS = frozenset({1, 2, 3, 4, 5})


class DataContractError(ValueError):
    """Raised when a frame violates a structural or point-in-time contract."""


def _copy(frame: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame):
        raise DataContractError(f"expected pandas.DataFrame, got {type(frame).__name__}")
    if frame.columns.duplicated().any():
        duplicates = frame.columns[frame.columns.duplicated()].astype(str).tolist()
        raise DataContractError(f"duplicate column names: {duplicates}")
    return frame.copy(deep=True)


def _require_columns(frame: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise DataContractError(f"missing required columns: {missing}")


def _datetime_copy(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    result = _copy(frame)
    _require_columns(result, columns)
    for column in columns:
        converted = pd.to_datetime(result[column], errors="coerce")
        invalid = result[column].notna() & converted.isna()
        if invalid.any() or converted.isna().any():
            raise DataContractError(f"{column} contains missing or non-convertible timestamps")
        result[column] = converted
    return result


def _numeric_column(nullable: bool = True) -> pa.Column:
    return pa.Column(
        None,
        nullable=nullable,
        checks=[
            Check(lambda series: bool(pd.api.types.is_numeric_dtype(series.dtype)), error="must be numeric"),
            Check(lambda series: bool(np.isfinite(series.dropna().to_numpy(dtype=float)).all()), error="must be finite"),
        ],
    )


def validate_factor_frame(frame: pd.DataFrame, factor_columns: Iterable[str] | None = None) -> pd.DataFrame:
    result = _datetime_copy(frame, ["datetime"])
    _require_columns(result, ["instrument"])
    factors = list(factor_columns) if factor_columns is not None else [
        str(column) for column in result.columns if column not in {"datetime", "instrument"}
    ]
    if not factors:
        raise DataContractError("factor frame has no factor columns")
    _require_columns(result, factors)
    schema = pa.DataFrameSchema(
        {
            "datetime": pa.Column(pa.DateTime, nullable=False),
            "instrument": pa.Column(str, nullable=False, checks=Check.str_length(min_value=1)),
            **{column: _numeric_column(nullable=True) for column in factors},
        },
        unique=["datetime", "instrument"],
        strict=False,
        coerce=False,
    )
    validated = schema.validate(result, lazy=True)
    if "coverage" in validated.columns:
        pa.SeriesSchema(float, checks=Check.in_range(0, 1), nullable=True, coerce=True).validate(validated["coverage"])
    return validated


def validate_label_frame(frame: pd.DataFrame) -> pd.DataFrame:
    time_columns = ["feature_time", "label_start_time", "label_end_time"]
    result = _datetime_copy(frame, time_columns)
    _require_columns(result, ["instrument", "label"])
    schema = pa.DataFrameSchema(
        {
            "feature_time": pa.Column(pa.DateTime, nullable=False),
            "label_start_time": pa.Column(pa.DateTime, nullable=False),
            "label_end_time": pa.Column(pa.DateTime, nullable=False),
            "instrument": pa.Column(str, nullable=False, checks=Check.str_length(min_value=1)),
            "label": _numeric_column(nullable=True),
        },
        unique=["feature_time", "instrument"],
        checks=[
            Check(lambda data: bool((data["feature_time"] < data["label_start_time"]).all()), error="feature_time must precede label_start_time"),
            Check(lambda data: bool((data["label_start_time"] <= data["label_end_time"]).all()), error="label_start_time must not exceed label_end_time"),
        ],
        strict=False,
    )
    return schema.validate(result, lazy=True)


def validate_tradability_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = _copy(frame)
    required = ["can_buy", "can_sell", "tradability_score", "liquidity_bucket"]
    _require_columns(result, required)
    schema = pa.DataFrameSchema(
        {
            "can_buy": pa.Column(bool, nullable=False),
            "can_sell": pa.Column(bool, nullable=False),
            "tradability_score": pa.Column(None, nullable=True, checks=Check.in_range(0, 100)),
            "liquidity_bucket": pa.Column(None, nullable=True, checks=Check.isin(sorted(LIQUIDITY_BUCKETS))),
        },
        strict=False,
    )
    return schema.validate(result, lazy=True)


def validate_universe_intervals(frame: pd.DataFrame) -> pd.DataFrame:
    date_columns = ["start_date", "end_date", "selection_date", "effective_date"]
    result = _datetime_copy(frame, date_columns)
    _require_columns(result, ["instrument", "selection_reason"])
    schema = pa.DataFrameSchema(
        {
            "instrument": pa.Column(str, nullable=False, checks=Check.str_length(min_value=1)),
            **{column: pa.Column(pa.DateTime, nullable=False) for column in date_columns},
            "selection_reason": pa.Column(str, nullable=False, checks=Check.str_length(min_value=1)),
        },
        checks=[
            Check(lambda data: bool((data["selection_date"] < data["effective_date"]).all()), error="selection_date must precede effective_date"),
            Check(lambda data: bool((data["start_date"] <= data["end_date"]).all()), error="start_date must not exceed end_date"),
        ],
        strict=False,
    )
    validated = schema.validate(result, lazy=True)
    ordered = validated.sort_values(["instrument", "start_date", "end_date"])
    previous_end = ordered.groupby("instrument", sort=False)["end_date"].shift()
    overlap = previous_end.notna() & (ordered["start_date"] <= previous_end)
    if overlap.any():
        raise DataContractError(f"overlapping universe intervals: {int(overlap.sum())}")
    return validated


def _candidate_schema(role_column: str, roles: frozenset[str], include_columns: dict[str, pa.Column]) -> pa.DataFrameSchema:
    return pa.DataFrameSchema(
        {
            "factor": pa.Column(str, nullable=False, unique=True, checks=Check.str_length(min_value=1)),
            role_column: pa.Column(str, nullable=False, checks=Check.isin(sorted(roles))),
            "coverage": pa.Column(None, nullable=True, checks=Check.in_range(0, 1)),
            "missing_rate": pa.Column(None, nullable=True, checks=Check.in_range(0, 1)),
            **include_columns,
        },
        strict=False,
    )


def validate_screening_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = _copy(frame)
    _require_columns(result, ["factor", "role", "coverage", "missing_rate", "included"])
    schema = _candidate_schema("role", SCREENING_ROLES, {"included": pa.Column(bool, nullable=False)})
    validated = schema.validate(result, lazy=True)
    if ((validated["role"] == "holdout") & validated["included"]).any():
        raise DataContractError("holdout rows cannot be included")
    return validated


def validate_judgement_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = _copy(frame)
    required = ["factor", "judgement_role", "coverage", "missing_rate", "research_included", "downstream_default_included"]
    _require_columns(result, required)
    schema = _candidate_schema(
        "judgement_role",
        JUDGEMENT_ROLES,
        {
            "research_included": pa.Column(bool, nullable=False),
            "downstream_default_included": pa.Column(bool, nullable=False),
        },
    )
    validated = schema.validate(result, lazy=True)
    blocked_role = validated["judgement_role"].isin(PROBE_ROLES | {"holdout"})
    if (blocked_role & validated["downstream_default_included"]).any():
        raise DataContractError("holdout and probe rows cannot enter downstream defaults")
    return validated
