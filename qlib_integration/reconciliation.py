from __future__ import annotations

import numpy as np
import pandas as pd


DIFFERENCE_CATEGORIES = {
    "calendar_semantics",
    "price_semantics",
    "order_generation",
    "trade_constraint",
    "cost_model",
    "rounding",
    "valuation",
    "unknown",
}


def compare_numeric_series(
    reference: pd.Series,
    qlib: pd.Series,
    *,
    atol: float = 1e-8,
    rtol: float = 1e-10,
) -> pd.Series:
    left, right = reference.align(qlib, join="outer")
    return pd.Series(
        np.isclose(left.astype(float), right.astype(float), atol=atol, rtol=rtol, equal_nan=False),
        index=left.index,
    )


def semantic_difference(
    *,
    scenario_id: str,
    category: str,
    field: str,
    reference_value: object,
    qlib_value: object,
    expected: bool,
    reason: str,
) -> dict[str, object]:
    if category not in DIFFERENCE_CATEGORIES:
        raise ValueError(f"unsupported semantic difference category: {category}")
    return {
        "scenario_id": scenario_id,
        "category": category,
        "field": field,
        "reference_value": reference_value,
        "qlib_value": qlib_value,
        "expected": bool(expected),
        "reason": reason,
    }


def unknown_difference_count(inventory: pd.DataFrame) -> int:
    if inventory.empty:
        return 0
    return int((inventory["category"] == "unknown").sum())
