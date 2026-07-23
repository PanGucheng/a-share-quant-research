from __future__ import annotations

import pandas as pd
import pytest

from factor_research.alpha101_source import (
    assert_alpha101_axes,
    mask_raw_to_pit_membership,
)
from research_validation.factor_dependency import (
    classify_python_method,
    filter_only_reuse_allowed,
    validate_dependency_inventory,
)


SOURCE = """
def pure(x):
    return delay(x, 5)

def cross(x):
    return rank(x)

def mixed(x):
    return rank(delta(x, 10))

def unresolved(x):
    return dynamic_helper(x)
"""


def test_ast_dependency_classes() -> None:
    assert classify_python_method(SOURCE, "pure").dependency_class == "pure_time_series"
    assert classify_python_method(SOURCE, "cross").dependency_class == "cross_sectional"
    assert classify_python_method(SOURCE, "mixed").dependency_class == "mixed"
    assert classify_python_method(SOURCE, "unresolved").dependency_class == "unknown"


def test_unknown_and_fallback_are_fail_closed() -> None:
    assert not filter_only_reuse_allowed(
        "unknown", classification_proven=False, fallback_sensitive=False
    )
    assert not filter_only_reuse_allowed(
        "pure_time_series", classification_proven=True, fallback_sensitive=True
    )
    assert filter_only_reuse_allowed(
        "pure_time_series", classification_proven=True, fallback_sensitive=False
    )


def test_inventory_rejects_unsafe_reuse() -> None:
    frame = pd.DataFrame(
        {
            "factor": ["a"],
            "dependency_class": ["mixed"],
            "filter_only_reuse_allowed": [True],
        }
    )
    assert "non_time_series_filter_only_reuse" in validate_dependency_inventory(
        frame, ["a"]
    )


def test_alpha101_positional_axis_relabel_is_forbidden() -> None:
    reference = pd.DataFrame([[1.0]], index=pd.to_datetime(["2024-01-02"]), columns=["SH600000"])
    wrong_index = reference.copy()
    wrong_index.index = pd.to_datetime(["2024-01-03"])
    with pytest.raises(ValueError, match="positional relabel is forbidden"):
        assert_alpha101_axes(wrong_index, reference, "alpha_fixture")

    wrong_columns = reference.copy()
    wrong_columns.columns = ["SZ000001"]
    with pytest.raises(ValueError, match="positional relabel is forbidden"):
        assert_alpha101_axes(wrong_columns, reference, "alpha_fixture")


def test_alpha101_raw_is_masked_outside_pit_membership() -> None:
    raw = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2024-01-02", "2024-01-02"]),
            "instrument": ["SH600000", "SZ000001"],
            "$open": [1.0, 2.0],
            "$high": [1.0, 2.0],
            "$low": [1.0, 2.0],
            "$close": [1.0, 2.0],
            "$volume": [1.0, 2.0],
            "$amount": [1.0, 2.0],
        }
    )
    keys = raw.loc[raw["instrument"].eq("SH600000"), ["datetime", "instrument"]]
    result = mask_raw_to_pit_membership(raw, keys, membership_start="2024-01-02")
    assert result.loc[result["instrument"].eq("SH600000"), "$close"].notna().all()
    assert result.loc[result["instrument"].eq("SZ000001"), "$close"].isna().all()


def test_pct_change_does_not_bridge_pit_membership_gap() -> None:
    close = pd.DataFrame(
        {"SH600000": [10.0, float("nan"), 12.0]},
        index=pd.date_range("2024-01-02", periods=3),
    )
    returns = close.pct_change(fill_method=None)
    assert pd.isna(returns.iloc[1, 0])
    assert pd.isna(returns.iloc[2, 0])
