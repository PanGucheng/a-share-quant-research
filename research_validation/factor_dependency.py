from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


DEPENDENCY_CLASSES = {
    "pure_time_series",
    "cross_sectional",
    "mixed",
    "unknown",
}

_CROSS_SECTIONAL_CALLS = {"rank", "scale"}
_TIME_SERIES_CALLS = {
    "correlation",
    "covariance",
    "decay_linear",
    "delay",
    "delta",
    "rolling",
    "shift",
    "sma",
    "stddev",
    "sum",
    "ts_argmax",
    "ts_argmin",
    "ts_max",
    "ts_min",
    "ts_rank",
    "ts_sum",
}


@dataclass(frozen=True)
class DependencyEvidence:
    dependency_class: str
    cross_sectional_operator_present: bool
    max_lookback_trading_days: int | None
    evidence: str


def _call_name(node: ast.Call) -> str:
    function = node.func
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        return function.attr
    return ""


def classify_python_method(source: str, method_name: str) -> DependencyEvidence:
    """Classify one factor method from auditable AST evidence.

    Unknown is deliberate: syntax errors, absent methods, dynamic calls, and
    unrecognised helper calls cannot become filter-only reuse candidates.
    """

    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return DependencyEvidence("unknown", False, None, f"syntax_error:{error.msg}")
    method = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == method_name
        ),
        None,
    )
    if method is None:
        return DependencyEvidence("unknown", False, None, "method_not_found")

    calls = {_call_name(node) for node in ast.walk(method) if isinstance(node, ast.Call)}
    calls.discard("")
    cross = bool(calls & _CROSS_SECTIONAL_CALLS)
    temporal = bool(calls & _TIME_SERIES_CALLS)
    allowed_non_temporal = {
        "abs",
        "astype",
        "copy",
        "exp",
        "fillna",
        "log",
        "max",
        "min",
        "pow",
        "replace",
        "sign",
        "where",
    }
    unknown_calls = calls - _CROSS_SECTIONAL_CALLS - _TIME_SERIES_CALLS - allowed_non_temporal
    if unknown_calls:
        return DependencyEvidence(
            "unknown",
            cross,
            _max_numeric_window(method),
            "unrecognised_calls:" + ",".join(sorted(unknown_calls)),
        )
    dependency_class = (
        "mixed"
        if cross and temporal
        else "cross_sectional"
        if cross
        else "pure_time_series"
    )
    evidence = (
        f"ast_calls={','.join(sorted(calls)) or 'elementwise_only'};"
        f"cross={','.join(sorted(calls & _CROSS_SECTIONAL_CALLS)) or 'none'};"
        f"temporal={','.join(sorted(calls & _TIME_SERIES_CALLS)) or 'none'}"
    )
    return DependencyEvidence(
        dependency_class,
        cross,
        _max_numeric_window(method),
        evidence,
    )


def _max_numeric_window(node: ast.AST) -> int:
    values: list[int] = []
    for call in (item for item in ast.walk(node) if isinstance(item, ast.Call)):
        if _call_name(call) not in _TIME_SERIES_CALLS:
            continue
        for argument in call.args[1:]:
            if isinstance(argument, ast.Constant) and isinstance(argument.value, (int, float)):
                values.append(int(math.ceil(abs(float(argument.value)))))
    return max(values, default=0)


def qlib_expression_lookback(expression: str) -> int:
    """Return a conservative lookback from Qlib per-instrument expressions."""

    values = [
        int(match)
        for match in re.findall(
            r"(?:Ref|Mean|Std|Slope|Rsquare|Resi|Max|Min|Quantile|Rank|Sum|EMA|WMA|Corr)\([^,]+,\s*(\d+)",
            expression,
        )
    ]
    return max(values, default=0)


def filter_only_reuse_allowed(
    dependency_class: str,
    *,
    classification_proven: bool,
    fallback_sensitive: bool,
) -> bool:
    return (
        dependency_class == "pure_time_series"
        and classification_proven
        and not fallback_sensitive
    )


def validate_dependency_inventory(frame: pd.DataFrame, expected_factors: Iterable[str]) -> list[str]:
    errors: list[str] = []
    expected = set(expected_factors)
    actual = set(frame["factor"].astype(str)) if "factor" in frame else set()
    if actual != expected:
        errors.append(
            f"factor_set_mismatch:missing={len(expected - actual)},extra={len(actual - expected)}"
        )
    if frame["factor"].duplicated().any():
        errors.append("duplicate_factors")
    invalid = sorted(set(frame["dependency_class"]) - DEPENDENCY_CLASSES)
    if invalid:
        errors.append(f"invalid_dependency_classes:{invalid}")
    unsafe = frame.loc[
        frame["dependency_class"].ne("pure_time_series")
        & frame["filter_only_reuse_allowed"].astype(bool)
    ]
    if not unsafe.empty:
        errors.append("non_time_series_filter_only_reuse")
    unknown_reuse = frame.loc[
        frame["dependency_class"].eq("unknown")
        & frame["filter_only_reuse_allowed"].astype(bool)
    ]
    if not unknown_reuse.empty:
        errors.append("unknown_filter_only_reuse")
    return errors
