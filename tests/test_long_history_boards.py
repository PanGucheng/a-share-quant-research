import numpy as np
import pandas as pd
import pytest

from factor_research.long_history_boards import METRICS, STATS, ECONOMIC_COLUMNS, descriptive_board


def inputs():
    inventory = pd.DataFrame({"factor": ["x"], "research_usable": [True], "canonical_factor_id": ["id"],
                              "source": ["fixture"], "economic_family": ["risk"],
                              "authoritative_semantics": ["raw"], "lineage_hash": ["fixed"]})
    periods = [("full", "full", 2800, 40/2800)]
    periods += [(str(y), "annual", 200, .04 if y <= 2014 else (-.02 if y <= 2017 else .01)) for y in range(2010, 2024)]
    periods += [("A", "signal_era", 1000, .04), ("B", "signal_era", 600, -.02),
                ("C", "signal_era", 600, .01), ("D", "signal_era", 600, .01)]
    rows = []
    for metric in METRICS:
        for name, kind, n, ic_mean in periods:
            mean = ic_mean
            if metric.startswith("alphalens_q") and metric[-1].isdigit():
                mean = int(metric[-1]) * .001
            rows.append({"factor": "x", "metric": metric, "period_id": name, "period_type": kind,
                         "actual_signal_start": "2010-01-29", "actual_signal_end": "2023-11-30",
                         "max_label_exit_date": "2023-12-29", "label": "label_20d_t1",
                         "universe": "canonical_practical_raw", **{s: .1 for s in STATS},
                         "mean": mean, "valid_dates": n})
    quality = pd.DataFrame({"factor": ["x"], "rows": [10000], "finite_count": [9000], "missing_count": [1000],
                            "infinite_count": [0], "coverage": [.9], "first_finite_date": ["2010-01-29"],
                            "last_finite_date": ["2023-12-29"], "min_count_variable_dates": [2800]})
    fdr = pd.DataFrame({"factor": ["x"], "status": ["available"], "raw_p_value": [.01], "fdr_bh_q_value": [.02],
                        "fdr_by_q_value": [.04], "observation_count": [2800], "eligible_segment_count": [1],
                        "contiguous_segment_count": [1], "eligible_block_count": [2781]})
    economic = pd.DataFrame({c: ["x"] for c in ECONOMIC_COLUMNS})
    return inventory, pd.DataFrame(rows), quality, fdr, economic


def test_era_contribution_leave_one_out_and_raw_quantile_shape():
    board = descriptive_board(*inputs()).iloc[0]
    assert board.alphalens_quantile_monotonicity_raw == pytest.approx(1.)
    assert board.max_absolute_era_contribution_share == pytest.approx(40/64)
    assert board.worst_leave_one_era_out_directional_mean == pytest.approx(0.)
    assert board.annual_direction_agreement == pytest.approx(11/14)
    assert board.worst_directional_era_mean == -.02
    assert board.alphalens_candidate_status == "not_evaluated"


def test_evidence_ignores_legacy_outcomes_but_rejects_recent_dates_and_missing_views():
    inventory, metrics, quality, fdr, economic = inputs()
    original = descriptive_board(inventory, metrics, quality, fdr, economic)
    for v in (1e8, -1e8):
        changed = descriptive_board(inventory, metrics.assign(recent_2024=v), quality,
                                    fdr, economic.assign(global_coverage=v, expected_direction=v, old_selected=v))
        pd.testing.assert_frame_equal(changed, original, check_exact=True)
    metrics.loc[0, "max_label_exit_date"] = "2024-01-02"
    with pytest.raises(ValueError, match="outside mature"):
        descriptive_board(inventory, metrics, quality, fdr, economic)
    metrics.loc[0, "max_label_exit_date"] = "2023-12-29"
    with pytest.raises(ValueError, match="missing required"):
        descriptive_board(inventory, metrics.iloc[1:], quality, fdr, economic)


def test_missing_quantile_shape_is_nan_not_zero():
    inventory, metrics, quality, fdr, economic = inputs()
    metrics.loc[metrics.metric.eq("alphalens_q3"), "mean"] = np.nan
    assert pd.isna(descriptive_board(inventory, metrics, quality, fdr, economic).iloc[0].alphalens_quantile_monotonicity_raw)
