import pandas as pd
import pytest

from research_validation.transparent_baseline import build_transparent_weights


def fixture_allowlist() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "outer_split_id": "split_001",
                "factor": f"f{index}",
                "feature_order": index,
                "cluster_id": f"c{index}",
                "frozen_direction": -1 if index == 0 else 1,
                "selection_frequency": 1.0 - index * 0.1,
                "upstream_fdr_q_value": 0.01 + index * 0.01,
                "upstream_fdr_pass": True,
                "stability_role": "stable_core",
                "holdout_clean": True,
                "allowlist_sha256": "a" * 64,
            }
            for index in range(3)
        ]
    )


def test_transparent_weights_are_split_scoped_normalized_and_direction_frozen() -> None:
    weights, manifests = build_transparent_weights(
        fixture_allowlist(), methods=["equal_weight", "stability_weight"], maximum_factor_weight=0.6
    )
    assert len(manifests) == 2
    assert weights.groupby(["outer_split_id", "method"])["weight"].sum().sub(1).abs().max() < 1e-12
    assert set(weights["direction"]) == {-1, 1}
    assert weights.groupby("method")["cluster_id"].nunique().eq(3).all()
    assert manifests["weights_sha256"].str.len().eq(64).all()


def test_transparent_weights_reject_test_fields() -> None:
    values = fixture_allowlist().assign(test_ic=0.1)
    with pytest.raises(ValueError, match="test/OOS"):
        build_transparent_weights(values, methods=["equal_weight"], maximum_factor_weight=0.6)
