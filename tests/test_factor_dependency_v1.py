from __future__ import annotations

import pandas as pd

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
