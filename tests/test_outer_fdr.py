import pandas as pd
import pytest

from research_validation.outer_fdr import compute_outer_split_fdr


def test_outer_fdr_produces_one_hypothesis_per_split_factor() -> None:
    dates = pd.bdate_range("2020-01-01", periods=60)
    projection = pd.DataFrame([
        {"outer_split_id": split, "datetime": date, "factor": factor, "rank_ic": value}
        for split in ("split_001", "split_002")
        for factor, value in (("a", 0.05), ("b", -0.03))
        for date in dates
    ])

    result = compute_outer_split_fdr(
        projection, metric="rank_ic", bootstrap_samples=20, block_length=5, random_seed=7,
        fdr_alpha=0.05, source_family="family", label_name="label", preprocessing_variant="raw",
    )

    assert len(result) == 4
    assert not result.duplicated(["outer_split_id", "factor"]).any()
    assert result.groupby("outer_split_id")["factor"].nunique().eq(2).all()
    assert result["family_scope"].eq("outer_split").all()


def test_outer_fdr_gap_aware_method_preserves_missing_date_boundaries() -> None:
    dates = pd.bdate_range("2020-01-01", periods=70)
    projection = pd.DataFrame(
        {
            "outer_split_id": "split_001",
            "datetime": dates,
            "factor": "a",
            "rank_ic": [0.02] * 30 + [float("nan")] * 5 + [0.03] * 35,
        }
    )
    result = compute_outer_split_fdr(
        projection,
        metric="rank_ic",
        bootstrap_samples=20,
        block_length=5,
        random_seed=7,
        fdr_alpha=0.05,
        source_family="family",
        label_name="label",
        preprocessing_variant="raw",
        bootstrap_method="gap_aware_moving_block",
    )
    assert result.loc[0, "bootstrap_method"] == "gap_aware_moving_block"
    assert result.loc[0, "contiguous_segment_count"] == 2


def test_outer_fdr_rejects_unknown_bootstrap_method() -> None:
    projection = pd.DataFrame(
        [{"outer_split_id": "s", "datetime": "2020-01-01", "factor": "a", "rank_ic": 0.1}]
    )
    with pytest.raises(ValueError, match="unsupported bootstrap method"):
        compute_outer_split_fdr(
            projection,
            metric="rank_ic",
            bootstrap_samples=20,
            block_length=5,
            random_seed=7,
            fdr_alpha=0.05,
            source_family="family",
            label_name="label",
            preprocessing_variant="raw",
            bootstrap_method="unknown",
        )
