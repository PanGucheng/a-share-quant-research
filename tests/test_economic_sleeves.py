from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from factor_research.economic_sleeves import (
    _monotonicity,
    build_economic_map,
    compute_split_local_eligibility,
    construct_scores,
    load_design,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = PROJECT_ROOT / "configs" / "economic_multi_factor_research_v1.yaml"


def test_design_freezes_historical_governance_and_directions() -> None:
    design = load_design(DESIGN_PATH)
    assert design["experiment_class"] == "post_observation_research"
    assert design["governance"]["historical_test_already_observed"] is True
    assert design["governance"]["unbiased_final_estimate"] is False
    assert design["governance"]["machine_learning_used"] is False
    assert design["construction"]["optimized_weights_allowed"] is False
    directions = [
        member["direction"]
        for sleeve in design["sleeves"]
        for member in sleeve["factors"]
    ]
    assert directions and set(directions).issubset({-1, 1})
    selected = [
        member["factor"]
        for sleeve in design["sleeves"]
        for member in sleeve["factors"]
    ]
    assert len(selected) == 39
    assert len(set(selected)) == 39


def test_design_rejects_post_result_direction_switch(tmp_path: Path) -> None:
    text = DESIGN_PATH.read_text(encoding="utf-8").replace(
        "result_driven_sign_changes_allowed: false",
        "result_driven_sign_changes_allowed: true",
    )
    path = tmp_path / "invalid.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="result-driven"):
        load_design(path)


def test_split_local_eligibility_uses_only_development_dates() -> None:
    dates = pd.date_range("2024-01-01", periods=4, freq="D")
    instruments = [f"SH{index:06d}" for index in range(120)]
    index = pd.MultiIndex.from_product([dates, instruments], names=["datetime", "instrument"])
    panel = index.to_frame(index=False)
    panel["stable"] = np.tile(np.arange(120, dtype=float), 4)
    panel["future_only"] = np.nan
    panel.loc[panel["datetime"].eq(dates[-1]), "future_only"] = np.arange(120, dtype=float)
    thresholds = {
        "minimum_row_coverage": 0.50,
        "minimum_finite_dates": 2,
        "minimum_cross_section": 100,
        "minimum_qualified_date_fraction": 0.80,
        "minimum_unique_values": 10,
    }
    eligibility = compute_split_local_eligibility(
        panel,
        pd.DatetimeIndex(dates[:3]),
        ["stable", "future_only"],
        thresholds,
        split_id="split_test",
    ).set_index("factor")
    assert bool(eligibility.loc["stable", "split_local_eligible"])
    assert not bool(eligibility.loc["future_only", "split_local_eligible"])
    assert eligibility.loc["future_only", "valid_count"] == 0


def test_subfamily_balancing_prevents_duplicate_measurement_dominance() -> None:
    design = {
        "construction": {"minimum_member_fraction": 0.5},
        "sleeves": [
            {
                "sleeve_id": "balanced",
                "factors": [
                    {"factor": "same_a", "direction": 1, "subfamily": "duplicated"},
                    {"factor": "same_b", "direction": 1, "subfamily": "duplicated"},
                    {"factor": "opposite", "direction": 1, "subfamily": "distinct"},
                ],
            }
        ],
        "archetypes": [],
    }
    panel = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2024-01-02"] * 3),
            "instrument": ["SH600001", "SH600002", "SH600003"],
            "same_a": [1.0, 2.0, 3.0],
            "same_b": [1.0, 2.0, 3.0],
            "opposite": [3.0, 2.0, 1.0],
        }
    )
    eligibility = pd.DataFrame(
        {
            "factor": ["same_a", "same_b", "opposite"],
            "split_local_eligible": [True, True, True],
        }
    )
    scores, _ = construct_scores(panel, design, eligibility)
    assert np.allclose(scores["balanced"], 0.0)


def test_monotonicity_equal_weights_dates_instead_of_rows() -> None:
    first = pd.DataFrame(
        {
            "datetime": pd.Timestamp("2024-01-02"),
            "score": np.arange(1, 101, dtype=float),
            "label": [0.0] * 80 + [1.0] * 20,
        }
    )
    second = pd.DataFrame(
        {
            "datetime": pd.Timestamp("2024-01-03"),
            "score": np.arange(1, 6, dtype=float),
            "label": [100.0, 0.0, 0.0, 0.0, 0.0],
        }
    )
    values, spread, _ = _monotonicity(pd.concat([first, second]), "score", "label")
    assert values[0] == pytest.approx(50.0)
    assert values[-1] == pytest.approx(0.5)
    assert spread == pytest.approx(-49.5)


def test_economic_map_keeps_physical_qualification_distinct_from_economic_selection() -> None:
    design = load_design(DESIGN_PATH)
    member = design["sleeves"][0]["factors"][0]["factor"]
    inventory = pd.DataFrame(
        [
            {
                "name": member,
                "source": "mature_public",
                "economic_family": "Value",
                "economic_subfamily": "EarningsYield",
                "secondary_family": "",
                "required_fields": "pe_ttm",
                "definition": "1/pe_ttm",
                "notes": "",
                "lineage_status": "complete",
            },
            {
                "name": "opaque_factor",
                "source": "alpha360",
                "economic_family": "Multi",
                "economic_subfamily": "",
                "secondary_family": "",
                "required_fields": "$close,$volume",
                "definition": "opaque formula",
                "notes": "",
                "lineage_status": "complete",
            },
        ]
    )
    qualification = pd.DataFrame(
        {
            "factor": [member, "opaque_factor"],
            "research_usable": [True, True],
            "coverage": [1.0, 1.0],
            "qualified_month_fraction": [1.0, 1.0],
        }
    )
    economic_map = build_economic_map(inventory, qualification, design).set_index("factor")
    assert economic_map.loc[member, "research_role"] == "selected_sleeve_member"
    assert economic_map.loc[member, "primary_family"] == "Valuation"
    assert economic_map.loc[member, "sleeve_id"] == "value"
    assert economic_map.loc["opaque_factor", "primary_family"] == "OpaqueMultiInput"
    assert economic_map.loc["opaque_factor", "expected_direction"] == "ambiguous_not_used"
