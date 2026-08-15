from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from model_research.feature_eligibility import (
    apply_eligibility_thresholds,
    profile_feature_frame,
    validate_threshold_freeze,
)


def _frozen_config() -> dict[str, object]:
    fields = {
        "maximum_missing_rate": 0.5,
        "minimum_finite_dates": 1,
        "minimum_finite_samples": 2,
        "minimum_imputed_weighted_variance": 1e-12,
    }
    return {
        "thresholds": fields,
        "threshold_selection": {
            "reasons": [
                {
                    "threshold": field,
                    "authority": "feature_data_quality",
                    "reason": "synthetic feature-only test",
                }
                for field in fields
            ]
        },
    }


def test_threshold_freeze_requires_values_and_feature_only_reasons() -> None:
    config = _frozen_config()
    assert validate_threshold_freeze(config)["minimum_finite_samples"] == 2
    config["target_feature_count"] = 100
    with pytest.raises(ValueError, match="target feature count"):
        validate_threshold_freeze(config)


def test_profile_and_decisions_are_label_free_and_canonicalize_duplicates() -> None:
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2024-01-02", "2024-01-02", "2024-01-03"]),
            "instrument": ["A", "B", "A"],
            "f_a": [1.0, np.nan, 3.0],
            "f_b": [1.0, np.nan, 3.0],
            "f_bad": [np.nan, np.nan, np.nan],
        }
    )
    profile = profile_feature_frame(
        frame,
        factor_names=["f_a", "f_b", "f_bad"],
        outer_split_id="split_001",
    )
    canonical = profile.set_index("factor")["is_duplicate_canonical"].to_dict()
    assert canonical == {"f_a": True, "f_b": False, "f_bad": True}
    inventory = pd.DataFrame(
        {
            "name": ["f_a", "f_b", "f_bad"],
            "source": ["x", "x", "x"],
            "enabled": [True, True, True],
            "runnable": [True, True, True],
        }
    )
    dependencies = pd.DataFrame(
        {
            "factor": ["f_a", "f_b", "f_bad"],
            "source_family": ["x", "x", "x"],
            "dependency_class": ["pure_time_series"] * 3,
            "review_status": ["proven"] * 3,
        }
    )
    decisions = apply_eligibility_thresholds(
        profile,
        inventory=inventory,
        dependencies=dependencies,
        thresholds=validate_threshold_freeze(_frozen_config()),
    ).set_index("factor")
    assert bool(decisions.at["f_a", "data_qualified"])
    assert not bool(decisions.at["f_b", "data_qualified"])
    assert not bool(decisions.at["f_bad", "correctness_pass"])


def test_unknown_dependency_fails_correctness() -> None:
    profile = pd.DataFrame(
        {
            "outer_split_id": ["split_001"],
            "factor": ["f"],
            "total_rows": [2],
            "finite_rows": [2],
            "missing_rate": [0.0],
            "finite_dates": [2],
            "imputed_weighted_variance": [1.0],
            "is_duplicate_canonical": [True],
        }
    )
    inventory = pd.DataFrame(
        {"name": ["f"], "source": ["x"], "enabled": [True], "runnable": [True]}
    )
    dependencies = pd.DataFrame(
        {
            "factor": ["f"],
            "source_family": ["x"],
            "dependency_class": ["unknown"],
            "review_status": ["proven"],
        }
    )
    decision = apply_eligibility_thresholds(
        profile,
        inventory=inventory,
        dependencies=dependencies,
        thresholds=validate_threshold_freeze(_frozen_config()),
    ).iloc[0]
    assert not bool(decision["correctness_pass"])
