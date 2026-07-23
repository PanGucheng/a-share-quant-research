from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from scripts.run_full_research_feature_matrix_v4 import (
    _exact_value_comparison,
    batch_specs,
    matrix_v4_scope,
)


ROOT = Path(__file__).resolve().parents[1]


def test_matrix_v4_scope_is_frozen_to_669_factors_and_30_batches() -> None:
    config = yaml.safe_load(
        (ROOT / "configs/full_research_feature_matrix_v4.yaml").read_text(
            encoding="utf-8"
        )
    )
    scope = matrix_v4_scope(config, batch_specs(config))
    assert scope["batch_count"] == 30
    assert scope["factor_count"] == 669
    assert scope["reused_factor_count"] == 605
    assert scope["recomputed_factor_count"] == 64
    assert scope["cache_key_schema_version"] == 4


def test_exact_comparison_detects_nan_and_value_mutations() -> None:
    keys = {
        "datetime": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "instrument": ["SH600000", "SH600000"],
    }
    old = pd.DataFrame({**keys, "factor_a": [1.0, float("nan")]})
    same = old.copy()
    dependency = pd.DataFrame(
        {
            "factor": ["factor_a"],
            "source_family": ["alpha158"],
            "dependency_class": ["pure_time_series"],
            "filter_only_reuse_allowed": [True],
        }
    ).set_index("factor")
    receipt = _exact_value_comparison(old, same, ["factor_a"], dependency).iloc[0]
    assert bool(receipt["bit_identical"])
    assert receipt["difference_count"] == 0

    changed = old.copy()
    changed.loc[0, "factor_a"] = 2.0
    changed.loc[1, "factor_a"] = 0.0
    receipt = _exact_value_comparison(
        old, changed, ["factor_a"], dependency
    ).iloc[0]
    assert not bool(receipt["bit_identical"])
    assert receipt["difference_count"] == 2


def test_runner_rejects_non_complete_approval_manifest() -> None:
    source = (
        ROOT / "scripts/run_full_research_feature_matrix_v4.py"
    ).read_text(encoding="utf-8")
    assert 'approval_manifest["lineage_status"] != "complete"' in source
    assert 'bool(approval_manifest["code_dirty"])' in source
